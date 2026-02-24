"""Solver：Baseline 与 Defended 的最简实现。"""

from __future__ import annotations
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from core.prompts import (
    BASELINE_SYSTEM,
    SHIELD_SYSTEM,
    BASELINE_CHOICE_SYSTEM,
    SHIELD_CHOICE_SYSTEM,
)
from core.schemas import NormalizedQuery, SolveResult


class GeoSolver:
    def __init__(
        self,
        model_name: str,
        vision_model: Optional[str] = None,
    ):
        self.text_llm = ChatOpenAI(model="gpt-5-mini", temperature=1, 
            api_key="sk-dev-SwRsUOEq0sdQjYPyrWdU5fp4DmXLFXRvKvwf9CrdSEyaHuoC",
            base_url="https://sher.locker/v1",
        )
        self.defended_llm = ChatOpenAI(
            model="gpt-5-mini",
            temperature=1,
            api_key="sk-dev-SwRsUOEq0sdQjYPyrWdU5fp4DmXLFXRvKvwf9CrdSEyaHuoC",
            base_url="https://sher.locker/v1",
        )
        self.vision_model = vision_model or model_name

    def _build_messages(self, system_prompt: str, query: NormalizedQuery) -> list:
        if query.image_bytes:
            return [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": query.text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{query.image_b64}"
                            },
                        },
                    ]
                ),
            ]
        return [SystemMessage(content=system_prompt), HumanMessage(content=query.text)]

    def solve_baseline(self, query: NormalizedQuery) -> SolveResult:
        messages = self._build_messages(BASELINE_SYSTEM, query)
        raw = self.text_llm.invoke(messages).content
        return SolveResult(answer=raw, raw=raw)

    def solve_defended(self, query: NormalizedQuery) -> SolveResult:
        messages = self._build_messages(SHIELD_SYSTEM, query)
        raw = self.defended_llm.invoke(messages).content
        return SolveResult(answer=raw, raw=raw)

    def solve_baseline_choice(self, query: NormalizedQuery) -> SolveResult:
        messages = self._build_messages(BASELINE_CHOICE_SYSTEM, query)
        raw = self.text_llm.invoke(messages).content
        return SolveResult(answer=raw.strip(), raw=raw)

    def solve_defended_choice(self, query: NormalizedQuery) -> SolveResult:
        messages = self._build_messages(SHIELD_CHOICE_SYSTEM, query)
        raw = self.defended_llm.invoke(messages).content
        return SolveResult(answer=raw.strip(), raw=raw)
