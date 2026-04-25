"""
llm_adapter.py
User-based LLM adapter for StegVerse demo-suite-runner.

Supports multiple providers:
  - OpenAI (GPT-4, GPT-3.5)
  - Moonshot AI / Kimi (Kimi K2.6)
  - Anthropic (Claude)
  - Local/Ollama (self-hosted)

Design principles:
  - Provider-agnostic interface
  - Deterministic where possible (seed, temperature=0)
  - Receipt-tagged for every LLM call
  - Budget/cost tracking per session
  - Fail-closed on provider errors
"""

import os
import json
import hashlib
from typing import Dict, Any, Optional, List, Generator
from dataclasses import dataclass
from enum import Enum
import logging

# StegVerse imports
from receipt_id import get_receipt
from governed_action import GovernedAction, GateResult

logger = logging.getLogger("stegverse.llm")


class ProviderType(Enum):
    OPENAI = "openai"
    KIMI = "kimi"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class LLMConfig:
    provider: ProviderType
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: int = 30


class LLMResponse:
    """Structured LLM response with StegVerse metadata."""

    def __init__(
        self,
        content: str,
        receipt_id: str,
        provider: ProviderType,
        model: str,
        usage: Dict[str, int],
        confidence: float = 0.0,
        reasoning: str = "",
        error: Optional[str] = None
    ):
        self.content = content
        self.receipt_id = receipt_id
        self.provider = provider
        self.model = model
        self.usage = usage
        self.confidence = confidence
        self.reasoning = reasoning
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "receipt_id": self.receipt_id,
            "provider": self.provider.value,
            "model": self.model,
            "usage": self.usage,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "error": self.error
        }


class LLMAdapter:
    """
    Multi-provider LLM adapter with StegVerse governance integration.

    Every call is:
      1. Receipt-tagged
      2. Budget-checked
      3. Provider-routed
      4. Response-governed (optional gate on output)
    """

    def __init__(
        self,
        config: LLMConfig,
        gate: Optional[GovernedAction] = None,
        budget_limit: Optional[float] = None
    ):
        self.config = config
        self.gate = gate or GovernedAction("GCAT")
        self.budget_limit = budget_limit
        self.budget_used = 0.0
        self.call_count = 0

        # Initialize provider client
        self._client = self._init_client()

    def _init_client(self):
        """Initialize provider-specific client."""
        if self.config.provider == ProviderType.OPENAI:
            try:
                import openai
                return openai.OpenAI(
                    api_key=self.config.api_key or os.getenv("OPENAI_API_KEY"),
                    base_url=self.config.base_url
                )
            except ImportError:
                raise RuntimeError("OpenAI package not installed. Run: pip install openai")

        elif self.config.provider == ProviderType.KIMI:
            try:
                import openai  # Kimi uses OpenAI-compatible SDK
                return openai.OpenAI(
                    api_key=self.config.api_key or os.getenv("KIMI_API_KEY"),
                    base_url=self.config.base_url or "https://api.moonshot.cn/v1"
                )
            except ImportError:
                raise RuntimeError("OpenAI package required for Kimi. Run: pip install openai")

        elif self.config.provider == ProviderType.ANTHROPIC:
            try:
                import anthropic
                return anthropic.Anthropic(
                    api_key=self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
                )
            except ImportError:
                raise RuntimeError("Anthropic package not installed. Run: pip install anthropic")

        elif self.config.provider == ProviderType.LOCAL:
            try:
                import openai
                return openai.OpenAI(
                    base_url=self.config.base_url or "http://localhost:11434/v1",
                    api_key="ollama"  # Ollama doesn't need real key
                )
            except ImportError:
                raise RuntimeError("OpenAI package required for local. Run: pip install openai")

        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        apply_gate: bool = True
    ) -> LLMResponse:
        """
        Generate LLM response with full StegVerse governance.

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            context: Gate context
            apply_gate: Whether to run output through gate

        Returns:
            LLMResponse with receipt, confidence, and usage
        """
        # Budget check
        if self.budget_limit and self.budget_used >= self.budget_limit:
            receipt = get_receipt({"action": "llm_generate", "prompt_hash": self._hash(prompt)})
            return LLMResponse(
                content="",
                receipt_id=receipt,
                provider=self.config.provider,
                model=self.config.model,
                usage={},
                confidence=1.0,
                reasoning="Budget limit exceeded",
                error="BUDGET_EXCEEDED"
            )

        # Build gate input for pre-approval (optional)
        if apply_gate:
            gate_input = {
                "action": "query",
                "payload": {
                    "llm_request": True,
                    "prompt_hash": self._hash(prompt),
                    "provider": self.config.provider.value,
                    "model": self.config.model
                }
            }
            pre_approval = self.gate.evaluate(gate_input, context)
            if pre_approval["result"] != GateResult.ALLOW:
                return LLMResponse(
                    content="",
                    receipt_id=pre_approval["receipt_id"],
                    provider=self.config.provider,
                    model=self.config.model,
                    usage={},
                    confidence=pre_approval["confidence"],
                    reasoning=pre_approval["reasoning"],
                    error="GATE_DENIED"
                )

        # Execute LLM call
        receipt = get_receipt({"action": "llm_generate", "prompt_hash": self._hash(prompt)})

        try:
            response = self._call_provider(prompt, system_prompt)

            # Update budget (approximate)
            tokens_used = response["usage"].get("total_tokens", 0)
            self.budget_used += self._estimate_cost(tokens_used)
            self.call_count += 1

            # Optional: Gate the output
            if apply_gate:
                output_gate = self.gate.evaluate({
                    "action": "verify",
                    "payload": {"llm_output_hash": self._hash(response["content"])}
                }, context)
                confidence = output_gate["confidence"]
                reasoning = output_gate["reasoning"]
            else:
                confidence = 0.85  # Default confidence when ungated
                reasoning = "LLM output generated without post-gate verification"

            return LLMResponse(
                content=response["content"],
                receipt_id=receipt,
                provider=self.config.provider,
                model=self.config.model,
                usage=response["usage"],
                confidence=confidence,
                reasoning=reasoning
            )

        except Exception as e:
            return LLMResponse(
                content="",
                receipt_id=receipt,
                provider=self.config.provider,
                model=self.config.model,
                usage={},
                confidence=1.0,
                reasoning=f"Provider error: {str(e)}",
                error=str(e)
            )

    def _call_provider(self, prompt: str, system_prompt: Optional[str]) -> Dict[str, Any]:
        """Provider-specific API call."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if self.config.provider in (ProviderType.OPENAI, ProviderType.KIMI, ProviderType.LOCAL):
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        elif self.config.provider == ProviderType.ANTHROPIC:
            response = self._client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=messages
            )
            return {
                "content": response.content[0].text,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            }

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _estimate_cost(self, tokens: int) -> float:
        """Rough cost estimate per 1K tokens."""
        rates = {
            ProviderType.OPENAI: 0.03,
            ProviderType.KIMI: 0.015,
            ProviderType.ANTHROPIC: 0.03,
            ProviderType.LOCAL: 0.0
        }
        return (tokens / 1000) * rates.get(self.config.provider, 0.03)


# Factory for easy instantiation
def create_adapter(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    gate: Optional[GovernedAction] = None,
    budget: Optional[float] = None
) -> LLMAdapter:
    """Create adapter from string provider name."""
    config = LLMConfig(
        provider=ProviderType(provider.lower()),
        model=model,
        api_key=api_key
    )
    return LLMAdapter(config, gate=gate, budget_limit=budget)
