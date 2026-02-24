"""5.3.2 难度自适应路由模块。"""

from __future__ import annotations
import json
import re
from dataclasses import asdict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from core.prompts import ROUTER_SYSTEM
from core.schemas import NormalizedQuery, RouteDecision


_SOCIAL_KEYWORDS = (
    "其他答题者",
    "还有六位答题者",
    "六位其他答题者",
    "other respondents",
    "six respondents",
    "group opinions",
)
_ROLE_LINE_PATTERN = re.compile(r"(^|\n)\s*[-*]?\s*[^:\n]{1,30}[:：]\s*[^\n]+", re.UNICODE)
_OPTION_LINE_PATTERN = re.compile(r"(^|\n)\s*[A-E][\.\):：]\s*", re.IGNORECASE)


class TaskRouter:
    def __init__(self, model_name: str, temperature: float = 0.0):
        self.llm = ChatOpenAI(
            model="gpt-5-mini",
            temperature=1,
            api_key="sk-dev-SwRsUOEq0sdQjYPyrWdU5fp4DmXLFXRvKvwf9CrdSEyaHuoC",
            base_url="https://sher.locker/v1",
        )

    @staticmethod
    def _has_social_guidance_structure(text: str) -> bool:
        normalized = (text or "").lower()
        if any(keyword in normalized for keyword in _SOCIAL_KEYWORDS):
            return True
        role_lines = _ROLE_LINE_PATTERN.findall(text or "")
        return len(role_lines) >= 2

    @staticmethod
    def _build_social_reason(query: NormalizedQuery, existing_reason: str) -> str:
        text = query.text or ""
        option_hits = len(_OPTION_LINE_PATTERN.findall(text))

        social_evidence = (
            "Detected multi-role peer-answer structure (e.g., respondent-role statements and potential consensus/split cues), "
            "which introduces social-conformity pressure."
        )
        content_risks: list[str] = []
        if option_hits >= 3:
            content_risks.append("multiple close options require fine-grained discrimination")
        if query.image_b64:
            content_risks.append("image input increases visual-spatial interpretation burden")
        if any(token in text for token in ("经纬", "遥感", "空间", "图层", "坐标", "projection", "spatial")):
            content_risks.append("task likely needs GIS domain reasoning rather than social voting")
        if not content_risks:
            content_risks.append(
                "task still requires independent verification under uncertainty, making social guidance risky"
            )

        task_evidence = "Task/content risk evidence: " + "; ".join(content_risks) + "."
        reason = f"Social evidence: {social_evidence} {task_evidence}"
        if existing_reason:
            reason = f"{reason} Router note: {existing_reason}"
        return reason

    def _enforce_social_high_risk(self, query: NormalizedQuery, decision: RouteDecision) -> RouteDecision:
        if not self._has_social_guidance_structure(query.text):
            return decision
        return RouteDecision(
            layer=decision.layer or "Geo-Application",
            risk="HIGH",
            reason=self._build_social_reason(query, decision.reason),
        )

    def route(self, query: NormalizedQuery) -> RouteDecision:
        prompt = f"任务描述: {query.text}\n"
        if query.image_b64:
            prompt += "包含图像输入。"

        messages = [SystemMessage(content=ROUTER_SYSTEM), HumanMessage(content=prompt)]
        raw = self.llm.invoke(messages).content

        try:
            data = json.loads(raw)
            decision = RouteDecision(
                layer=str(data.get("layer", "")),
                risk=str(data.get("risk", "")),
                reason=str(data.get("reason", "")),
            )
            return self._enforce_social_high_risk(query, decision)
        except Exception:
            fallback = RouteDecision(layer="Geo-Application", risk="HIGH", reason="Parse failed")
            return self._enforce_social_high_risk(query, fallback)

    def debug_dict(self, decision: RouteDecision) -> dict:
        return asdict(decision)
