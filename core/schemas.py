from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class NormalizedQuery:
    """5.3.1 多模态数据处理模块输出结构。"""

    text: str
    image_b64: Optional[str] = None
    image_bytes: Optional[bytes] = None


@dataclass
class RouteDecision:
    """5.3.2 难度自适应路由模块输出结构。"""

    layer: str
    risk: str
    reason: str


@dataclass
class SolveResult:
    """Solver 输出结构。"""

    answer: str
    raw: str


@dataclass
class VQASample:
    """评测样本结构。"""

    sample_id: str
    title: str
    question: str
    options: dict
    answer: str
    tag: str
    image_path: Optional[str] = None
