import pytest
from backend import research


def test_free_only_blocks_paid_models_and_all_embeddings(monkeypatch):
    monkeypatch.setenv("LLM_FREE_ONLY", "true")
    monkeypatch.setenv("LLM_API_KEY", "test-secret")
    monkeypatch.setenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("LLM_MODEL", "paid/model")
    monkeypatch.setattr(research, "request", lambda *a, **k: pytest.fail("No network call allowed"))
    with pytest.raises(ValueError, match="No paid request"):
        research.llm("test", "test")
    assert research.embed(["document"]) == [[]]


def test_free_router_preserves_json_requirement(monkeypatch):
    monkeypatch.setenv("LLM_FREE_ONLY", "true")
    monkeypatch.setenv("LLM_API_KEY", "test-secret")
    monkeypatch.setenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("LLM_MODEL", "openrouter/free")
    class Reply:
        def json(self): return {"choices": [{"message": {"content": '{"claims": []}'}}]}
    def request(method, url, **kwargs):
        assert url == "https://openrouter.ai/api/v1/chat/completions"
        assert kwargs["json"]["model"] == "openrouter/free"
        assert kwargs["json"]["response_format"] == {"type": "json_object"}
        return Reply()
    monkeypatch.setattr(research, "request", request)
    assert research.llm("test", "test") == {"claims": []}


def test_malformed_provider_reply_is_actionable(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-secret")
    monkeypatch.setenv("LLM_FREE_ONLY", "false")
    class Reply:
        def json(self): return {"choices": [{"message": {"content": "not json"}}]}
    monkeypatch.setattr(research, "request", lambda *a, **k: Reply())
    with pytest.raises(ValueError, match="invalid structured answer"):
        research.llm("test", "test")
