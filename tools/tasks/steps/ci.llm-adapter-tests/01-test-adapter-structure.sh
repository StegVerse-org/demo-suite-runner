cd scripts
python -c "
from llm_adapter import LLMConfig, ProviderType, LLMAdapter, create_adapter, LLMResponse
config = LLMConfig(provider=ProviderType.LOCAL, model='llama2')
assert config.provider == ProviderType.LOCAL
assert config.temperature == 0.0
assert ProviderType.OPENAI.value == 'openai'
assert ProviderType.KIMI.value == 'kimi'
adapter = create_adapter('local', 'test-model')
assert adapter.config.provider == ProviderType.LOCAL
assert adapter.budget_used == 0.0
resp = LLMResponse('test', 'REC-TEST', ProviderType.LOCAL, 'm', {}, 0.5, 'reason')
d = resp.to_dict()
assert d['content'] == 'test'
assert d['confidence'] == 0.5
print('=== LLM ADAPTER TESTS PASSED ===')
"
