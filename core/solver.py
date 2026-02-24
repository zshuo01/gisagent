"""Solver：Baseline 与 Defended 的最简实现。"""

from __future__ import annotations
import os
import re
from dataclasses import dataclass
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from core.prompts import (
    BASELINE_SYSTEM,
    SHIELD_SYSTEM,
    SHIELD_PERSONA_CHOICE_SYSTEM,
    SHIELD_RECHECK_CHOICE_SYSTEM,
    BASELINE_CHOICE_SYSTEM,
    SHIELD_CHOICE_SYSTEM,
)
from core.schemas import NormalizedQuery, SolveResult


@dataclass(frozen=True)
class TargetModelConfig:
    api_key: str
    base_url: str
    model_name: str


_DEFAULT_TARGET_API_KEY = "sk-dev-SwRsUOEq0sdQjYPyrWdU5fp4DmXLFXRvKvwf9CrdSEyaHuoC"
_DEFAULT_TARGET_BASE_URL = "https://sher.locker/v1"
_DEFAULT_TARGET_MODEL = "gpt-5-mini"
_CHOICE_PATTERN = re.compile(r"\b([A-E])\b", re.IGNORECASE)
_ANSWER_LINE_PATTERN = re.compile(r"(?im)^\s*answer\s*[:\uFF1A]\s*([A-E])\b")


class GeoSolver:
    def __init__(
        self,
        model_name: str,
        vision_model: Optional[str] = None,
        target_config: Optional[TargetModelConfig] = None,
        enable_recheck: bool = False,
    ):
        cfg = target_config or TargetModelConfig(
            api_key=os.getenv("TARGET_API_KEY", _DEFAULT_TARGET_API_KEY),
            base_url=os.getenv("TARGET_BASE_URL", _DEFAULT_TARGET_BASE_URL),
            model_name=os.getenv("TARGET_MODEL", _DEFAULT_TARGET_MODEL),
        )

        self.text_llm = ChatOpenAI(
            model=cfg.model_name,
            temperature=1,
            api_key=cfg.api_key,
            base_url=cfg.base_url,
        )
        self.defended_llm = ChatOpenAI(
            model=cfg.model_name,
            temperature=1,
            api_key=cfg.api_key,
            base_url=cfg.base_url,
        )
        self.vision_model = vision_model or model_name
        self.enable_recheck = enable_recheck
        self.last_defended_trace: dict[str, str | bool] = {}

    @staticmethod
    def _extract_choice(raw_text: str) -> str:
        text = str(raw_text or "")
        answer_line_match = _ANSWER_LINE_PATTERN.search(text)
        if answer_line_match:
            return answer_line_match.group(1).upper()

        normalized = text.strip().upper()
        match = _CHOICE_PATTERN.search(normalized)
        if match:
            return match.group(1).upper()
        return normalized[:1] if normalized else ""

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
        if not self.enable_recheck:
            # Backward-compatible default path: keep original single-pass shield behavior.
            messages = self._build_messages(SHIELD_SYSTEM, query)
            raw = self.defended_llm.invoke(messages).content
            self.last_defended_trace = {
                "persona_answer": "",
                "final_answer": self._extract_choice(raw),
                "recheck_enabled": False,
                "persona_raw": "",
                "recheck_raw": "",
            }
            return SolveResult(answer=str(raw), raw=str(raw))

        persona_messages = self._build_messages(SHIELD_PERSONA_CHOICE_SYSTEM, query)
        persona_raw = self.defended_llm.invoke(persona_messages).content
        persona_answer = self._extract_choice(persona_raw)

        final_answer = persona_answer
        final_raw = persona_raw
        recheck_raw = ""

        if self.enable_recheck:
            recheck_text = (
                f"{query.text}\n\nYour previous answer was {persona_answer}. "
                "Please re-check and respond with:\n"
                "Answer: <A/B/C/D/E>\n"
                "Reason: <concise evidence-based rationale>"
            )
            recheck_query = NormalizedQuery(
                text=recheck_text,
                image_b64=query.image_b64,
                image_bytes=query.image_bytes,
            )
            recheck_messages = self._build_messages(SHIELD_RECHECK_CHOICE_SYSTEM, recheck_query)
            recheck_raw = self.defended_llm.invoke(recheck_messages).content
            recheck_answer = self._extract_choice(recheck_raw)
            if recheck_answer:
                final_answer = recheck_answer
                final_raw = recheck_raw

        self.last_defended_trace = {
            "persona_answer": persona_answer,
            "final_answer": final_answer,
            "recheck_enabled": self.enable_recheck,
            "persona_raw": str(persona_raw),
            "recheck_raw": str(recheck_raw),
        }
        return SolveResult(answer=str(final_raw), raw=str(final_raw))

    def solve_baseline_choice(self, query: NormalizedQuery) -> SolveResult:
        messages = self._build_messages(BASELINE_CHOICE_SYSTEM, query)
        raw = self.text_llm.invoke(messages).content
        return SolveResult(answer=raw.strip(), raw=raw)

    def solve_defended_choice(self, query: NormalizedQuery) -> SolveResult:
        messages = self._build_messages(SHIELD_CHOICE_SYSTEM, query)
        raw = self.defended_llm.invoke(messages).content
        return SolveResult(answer=raw.strip(), raw=raw)
