"""5.3.2 难度自适应路由模块。"""

from __future__ import annotations
import os
import json
from dataclasses import asdict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from core.prompts import ROUTER_SYSTEM
from core.schemas import NormalizedQuery, RouteDecision


class TaskRouter:
    def __init__(self, model_name: str, temperature: float = 0.0):
        self.llm = ChatOpenAI(
            model="gpt-5-mini",
            temperature=1,
            api_key="sk-dev-SwRsUOEq0sdQjYPyrWdU5fp4DmXLFXRvKvwf9CrdSEyaHuoC",
            base_url="https://sher.locker/v1",
        )

    def route(self, query: NormalizedQuery) -> RouteDecision:
        prompt = f"任务描述: {query.text}\n"
        if query.image_b64:
            prompt += "包含图像输入。"

        messages = [SystemMessage(content=ROUTER_SYSTEM), HumanMessage(content=prompt)]
        raw = self.llm.invoke(messages).content

        try:
            data = json.loads(raw)
            return RouteDecision(
                layer=str(data.get("layer", "")),
                risk=str(data.get("risk", "")),
                reason=str(data.get("reason", "")),
            )
        except Exception:
            return RouteDecision(layer="Geo-Application", risk="HIGH", reason="Parse failed")

    def debug_dict(self, decision: RouteDecision) -> dict:
        return asdict(decision)
