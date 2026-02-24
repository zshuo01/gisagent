from core.router import TaskRouter
from core.schemas import NormalizedQuery


def test_router_parse_failure_fallback(monkeypatch):
    router = TaskRouter(model_name="fake-model")

    class Dummy:
        def invoke(self, messages):
            class R:
                content = "not json"

            return R()

    router.llm = Dummy()

    decision = router.route(NormalizedQuery(text="test"))
    assert decision.risk == "HIGH"
