"""最简数据集加载器（5.4 系统测试支持）。"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List

from core.schemas import VQASample


def _iter_json_files(data_dir: str | Path) -> Iterable[Path]:
    return Path(data_dir).rglob("*.json")


def load_dataset(data_dir: str | Path) -> List[VQASample]:
    samples: List[VQASample] = []
    for json_path in _iter_json_files(data_dir):
        with json_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
            
        # 兼容性处理：如果 payload 不是列表，将其转换为列表统一处理
        if not isinstance(payload, list):
            payload = [payload]

        # 增加一层循环，遍历列表中的每一个字典元素
        for item in payload:
            # 现在 item 是字典了，可以安全地使用 .get()
            question_set = item.get("question_set", {})
            title = question_set.get("title", "")
            image_name = question_set.get("image")
            questions = question_set.get("questions", [])

            for q in questions:
                qid = q.get("id")
                sample_id = f"{json_path.stem}#{qid}"
                image_path = None
                if image_name:
                    image_path = str((json_path.parent / image_name).resolve())

                samples.append(
                    VQASample(
                        sample_id=sample_id,
                        title=title,
                        question=q.get("question", ""),
                        options=q.get("options", {}),
                        answer=q.get("answer", ""),
                        tag=q.get("tag", ""),
                        image_path=image_path,
                    )
                )
    return samples


def format_mcq_prompt(sample: VQASample) -> str:
    options_text = "\n".join(
        [f"{k}. {v}" for k, v in sample.options.items() if v is not None]
    )
    return f"{sample.title}\n{sample.question}\n{options_text}".strip()


def sample_to_dict(sample: VQASample) -> dict:
    return asdict(sample)
