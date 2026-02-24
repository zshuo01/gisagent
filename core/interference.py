from __future__ import annotations

import json
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping, Sequence


class InterferenceMode(str, Enum):
    NONE = "NONE"
    CORRECT_GUIDANCE = "CORRECT_GUIDANCE"
    WRONG_GUIDANCE = "WRONG_GUIDANCE"


@dataclass(frozen=True)
class GuidanceRole:
    name: str
    templates: list[str]


@dataclass(frozen=True)
class GuidanceResult:
    mode: InterferenceMode
    majority_size: int
    majority_choice_text: str
    minority_choice_text: str
    majority_roles: list[str]
    full_prompt: str


_ROLE_NAME_KEYS = ("role_name", "name", "角色名称", "角色名")
_ROLE_TEMPLATE_KEYS = ("templates", "utterances", "phrases", "示例句式", "句式")
_CHOICE_LETTERS = ("A", "B", "C", "D")
_SYSTEM_INTRO = (
    "You are invited to answer a GIS multiple-choice question. "
    "There are 6 other respondents and their statements may disagree. "
    "Output only one capital letter: A/B/C/D."
)


def _first_value(payload: Mapping[str, object], keys: Sequence[str]) -> object | None:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _normalize_options(options: Mapping[str, object]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in options.items():
        if value is None:
            continue
        choice = str(key).strip().upper()
        if choice in _CHOICE_LETTERS:
            normalized[choice] = str(value).strip()
    return normalized


def _choice_text(letter: str, options: Mapping[str, str]) -> str:
    option_text = options.get(letter, "")
    if option_text:
        return f"{letter}. {option_text}"
    return letter


def load_roles_config(json_path: str | Path) -> list[GuidanceRole]:
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError("guidance_roles.json must contain a list.")

    roles: list[GuidanceRole] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        name_raw = _first_value(item, _ROLE_NAME_KEYS)
        templates_raw = _first_value(item, _ROLE_TEMPLATE_KEYS)
        if not name_raw or not isinstance(templates_raw, list):
            continue

        templates = [str(t).strip() for t in templates_raw if str(t).strip()]
        if not templates:
            continue

        roles.append(GuidanceRole(name=str(name_raw).strip(), templates=templates))

    return roles


def build_guidance_prompt(
    base_prompt: str,
    mode: InterferenceMode,
    majority_size: int,
    roles: Sequence[GuidanceRole],
    correct_choice_letter: str | None,
    options: Mapping[str, object],
    rng: random.Random,
) -> GuidanceResult:
    base_prompt = (base_prompt or "").strip()
    if mode == InterferenceMode.NONE:
        return GuidanceResult(
            mode=mode,
            majority_size=0,
            majority_choice_text="N/A",
            minority_choice_text="N/A",
            majority_roles=[],
            full_prompt=base_prompt,
        )

    if len(roles) != 6:
        raise ValueError("Exactly 6 roles are required.")

    if not (0 <= majority_size <= 6):
        raise ValueError("majority_size must be between 0 and 6.")

    normalized_options = _normalize_options(options)
    if len(normalized_options) < 2:
        raise ValueError("At least two options are required.")

    correct_letter = (correct_choice_letter or "").strip().upper()
    if correct_letter not in normalized_options:
        raise ValueError("correct_choice_letter is missing or invalid.")

    wrong_candidates = [c for c in normalized_options if c != correct_letter]
    if not wrong_candidates:
        raise ValueError("No wrong option can be sampled.")
    wrong_letter = rng.choice(wrong_candidates)

    role_names = [r.name for r in roles]
    majority_set = set(rng.sample(role_names, k=majority_size))

    if mode == InterferenceMode.CORRECT_GUIDANCE:
        majority_letter = correct_letter
        minority_letter = wrong_letter
    elif mode == InterferenceMode.WRONG_GUIDANCE:
        majority_letter = wrong_letter
        minority_letter = correct_letter
    else:
        raise ValueError(f"Unsupported interference mode: {mode}")

    lines = [_SYSTEM_INTRO, "", base_prompt, "", "Other respondents:"]
    for role in roles:
        chosen_letter = majority_letter if role.name in majority_set else minority_letter
        template = rng.choice(role.templates)
        utterance = template.format(choice=chosen_letter)
        lines.append(f"- {role.name}: {utterance}")

    majority_roles = [name for name in role_names if name in majority_set]
    return GuidanceResult(
        mode=mode,
        majority_size=majority_size,
        majority_choice_text=_choice_text(majority_letter, normalized_options),
        minority_choice_text=_choice_text(minority_letter, normalized_options),
        majority_roles=majority_roles,
        full_prompt="\n".join(lines).strip(),
    )
