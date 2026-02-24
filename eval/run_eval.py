import os
import re

from dotenv import load_dotenv

from core.dataset import load_dataset, format_mcq_prompt
from core.mm_processor import normalize_input
from core.router import TaskRouter
from core.solver import GeoSolver


CHOICE_RE = re.compile(r"[ABCD]")


def _extract_choice(text: str) -> str:
    match = CHOICE_RE.search(text or "")
    return match.group(0) if match else ""


def main() -> None:
    load_dotenv()

    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    vision_model = os.getenv("VISION_MODEL", model_name)

    router = TaskRouter(model_name=model_name)
    solver = GeoSolver(model_name=model_name, vision_model=vision_model)

    samples = load_dataset("data")
    if not samples:
        print("No samples found in data/ directory.")
        return

    base_correct = 0
    ours_correct = 0

    for sample in samples:
        text = format_mcq_prompt(sample)
        image_bytes = None
        if sample.image_path:
            try:
                with open(sample.image_path, "rb") as f:
                    image_bytes = f.read()
            except FileNotFoundError:
                image_bytes = None

        query = normalize_input(text, image_bytes)
        decision = router.route(query)

        base_pred_raw = solver.solve_baseline_choice(query).answer
        base_pred = _extract_choice(base_pred_raw)

        if decision.risk.upper() == "HIGH":
            ours_pred_raw = solver.solve_defended_choice(query).answer
            ours_pred = _extract_choice(ours_pred_raw)
        else:
            ours_pred = base_pred

        gold = sample.answer.strip().upper()

        base_correct += 1 if base_pred == gold else 0
        ours_correct += 1 if ours_pred == gold else 0

        print(
            f"{sample.sample_id} | {sample.tag} | {decision.risk} | "
            f"gold={gold} | base={base_pred} | ours={ours_pred}"
        )

    total = len(samples)
    print("\nSummary:")
    print(f"Baseline Acc: {base_correct}/{total} = {base_correct/total:.2%}")
    print(f"Ours Acc: {ours_correct}/{total} = {ours_correct/total:.2%}")


if __name__ == "__main__":
    main()
