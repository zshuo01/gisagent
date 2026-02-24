"""5.3.1 多模态数据处理模块。"""

from __future__ import annotations

import base64
from typing import Optional

from core.schemas import NormalizedQuery


def _b64encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def normalize_input(user_text: str, image_bytes: Optional[bytes]) -> NormalizedQuery:
    """标准化文本 + 图像输入。"""

    user_text = (user_text or "").strip()
    if image_bytes:
        return NormalizedQuery(
            text=user_text,
            image_b64=_b64encode_image(image_bytes),
            image_bytes=image_bytes,
        )
    return NormalizedQuery(text=user_text)
