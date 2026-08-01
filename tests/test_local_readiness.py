from api.services import local_readiness


def test_runtime_requires_openai_key():
    assert local_readiness.format_llm_provider_key_names() == "OPENAI_API_KEY"
    assert local_readiness.has_llm_provider_key({"OPENAI_API_KEY": "sk-test"})
    assert not local_readiness.has_llm_provider_key({"UNRELATED_API_KEY": "test"})
