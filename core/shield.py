"""5.3.3 专家角色与推理引导模块 + Controller。"""

from __future__ import annotations

from core.schemas import NormalizedQuery, RouteDecision, SolveResult
from core.router import TaskRouter
from core.solver import GeoSolver


class GeoShieldSystem:
    def __init__(self, router: TaskRouter, solver: GeoSolver):
        self.router = router
        self.solver = solver

    def run(self, query: NormalizedQuery) -> dict:
        decision = self.router.route(query)
        baseline = self.solver.solve_baseline(query)
        defended: SolveResult | None = None

        if decision.risk.upper() == "HIGH":
            defended = self.solver.solve_defended(query)

        return {
            "route": decision,
            "baseline": baseline,
            "defended": defended,
        }
