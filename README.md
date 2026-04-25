# StegVerse Demo Suite Runner — Deploy Bundle

## Files Included

| File | Purpose |
|---|---|
| `scripts/receipt_id.py` | Deterministic receipt ID generation |
| `scripts/governed_action.py` | Gate action handler with FAIL_CLOSED fix |
| `scripts/governed_mutation.py` | State mutation with deterministic logging |
| `scripts/llm_adapter.py` | Multi-provider LLM adapter (OpenAI, Kimi, Anthropic, Local) |
| `scripts/demo_suite_runner.py` | Main 3-pass weighted test runner |
| `.github/workflows/ci.txt` | Repo-agnostic CI workflow (rename to `.yml` after upload) |
| `requirements.txt` | Python dependencies |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run deterministic demo suite
python scripts/demo_suite_runner.py --seed "my-test-seed" --tests 10 --mode deterministic --cache-clear

# 3. Run with LLM analysis
python scripts/demo_suite_runner.py --seed "my-test-seed" --llm-provider kimi --llm-model "kimi-k2-6" --output result.json
```

## Key Design Decisions

1. **Receipt Before Evaluation**: `receipt_id.py` generates receipts BEFORE gate evaluation, fixing the malformed_request FAIL_CLOSED bug.
2. **Deterministic by Default**: All tests reproducible via `--seed`. Same seed → same receipts → same results.
3. **3-Pass Weighted Testing**: Pass 2 biases ~30% away from Pass 1 dominant result. Pass 3 biases ~50% away from aggregate.
4. **LLM Adapter**: Provider-agnostic with budget tracking, receipt tagging, and optional gate integration.
5. **CI Cache Clear**: Every workflow run starts with cache clear to prevent state leakage between runs.

## Integration Points

- **StegDB**: Wire `_log_mutation()` in `governed_mutation.py` and `_log()` in `governed_action.py` to your StegDB API.
- **GCAT/BCAT**: Replace `_run_gate()` in `governed_action.py` with your actual invariant checks.
- **LLM Providers**: Set API keys via environment variables (`OPENAI_API_KEY`, `KIMI_API_KEY`, `ANTHROPIC_API_KEY`).

## Deploy Checklist

- [ ] Rename `.github/workflows/ci.txt` to `.github/workflows/ci.yml`
- [ ] Add API keys to GitHub Secrets (if using LLM adapter in CI)
- [ ] Wire StegDB logging endpoints
- [ ] Replace placeholder gate logic with actual GCAT/BCAT invariants
- [ ] Test on target device (iPhone-compatible pathing verified)
