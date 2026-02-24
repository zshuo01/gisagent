from core.schemas import NormalizedQuery, RouteDecision
from core.shield import GeoShieldSystem


class DummyRouter:
    def __init__(self, risk: str):
        self.risk = risk

    def route(self, query):
        return RouteDecision(layer="Geo-Application", risk=self.risk, reason="")


class DummySolver:
    def solve_baseline(self, query):
        return "BASE"

    def solve_defended(self, query):
        return "DEF"


def test_shield_high_risk_triggers_defended():
    system = GeoShieldSystem(router=DummyRouter("HIGH"), solver=DummySolver())
    out = system.run(NormalizedQuery(text="hi"))
    assert out["defended"] == "DEF"


def test_shield_low_risk_skips_defended():
    system = GeoShieldSystem(router=DummyRouter("LOW"), solver=DummySolver())
    out = system.run(NormalizedQuery(text="hi"))
    assert out["defended"] is None
