import os
import random
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from core.mm_processor import normalize_input
from core.router import TaskRouter
from core.solver import GeoSolver, TargetModelConfig
from core.shield import GeoShieldSystem
from core.dataset import load_dataset, format_mcq_prompt
from core.interference import (
    InterferenceMode,
    build_guidance_prompt,
    load_roles_config,
)


load_dotenv()


def _read_image_bytes(uploaded_file) -> bytes | None:
    if uploaded_file is None:
        return None
    return uploaded_file.read()


def _read_path_bytes(path: str | None) -> bytes | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists():
        return None
    return file_path.read_bytes()


def _new_seed() -> int:
    return random.SystemRandom().randint(0, 2_147_483_647)


def _sync_interference_seed(mode_key: str, majority_size: int, reroll: bool) -> int:
    if "interference_seed" not in st.session_state:
        st.session_state["interference_seed"] = _new_seed()

    last_mode = st.session_state.get("interference_mode_key")
    last_majority = st.session_state.get("interference_majority_size")
    if reroll or last_mode != mode_key or last_majority != majority_size:
        st.session_state["interference_seed"] = _new_seed()

    st.session_state["interference_mode_key"] = mode_key
    st.session_state["interference_majority_size"] = majority_size
    return int(st.session_state["interference_seed"])


def main() -> None:
    st.title("抗干扰地理空间智能协作系统 MVP")

    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    vision_model = os.getenv("VISION_MODEL", model_name)

    router = TaskRouter(model_name=model_name)

    st.sidebar.header("数据集加载")
    data_dir = st.sidebar.text_input("data目录", value="data")
    use_dataset = st.sidebar.checkbox("从data加载题目", value=False)

    preset_text = ""
    preset_image_bytes = None
    selected_sample = None

    if use_dataset:
        samples = load_dataset(data_dir)
        sample_options = [s.sample_id for s in samples]
        if sample_options:
            selected = st.sidebar.selectbox("选择题目", sample_options)
            selected_sample = next(s for s in samples if s.sample_id == selected)
            preset_text = format_mcq_prompt(selected_sample)
            preset_image_bytes = _read_path_bytes(selected_sample.image_path)
            st.sidebar.write(f"Gold: {selected_sample.answer} | Tag: {selected_sample.tag}")
        else:
            st.sidebar.warning("data目录下未找到样本")

    st.sidebar.header("被测试模型配置")
    enable_target_config = st.sidebar.checkbox(
        "启用前端Target配置",
        value=bool(st.session_state.get("enable_target_config", False)),
    )
    st.session_state["enable_target_config"] = enable_target_config
    target_api_key = st.sidebar.text_input(
        "Target API Key",
        value=st.session_state.get("target_api_key", ""),
        type="password",
        disabled=not enable_target_config,
    )
    target_base_url = st.sidebar.text_input(
        "Target Base URL",
        value=st.session_state.get("target_base_url", ""),
        disabled=not enable_target_config,
    )
    target_model_name = st.sidebar.text_input(
        "Target Model Name",
        value=st.session_state.get("target_model_name", ""),
        disabled=not enable_target_config,
    )
    st.session_state["target_api_key"] = target_api_key
    st.session_state["target_base_url"] = target_base_url
    st.session_state["target_model_name"] = target_model_name

    enable_shield_recheck_default = str(os.getenv("ENABLE_SHIELD_RECHECK", "0")).lower() in (
        "1",
        "true",
        "yes",
    )
    enable_shield_recheck = st.sidebar.checkbox(
        "启用Shield二次复核(开启后使用Persona→Recheck)",
        value=bool(st.session_state.get("enable_shield_recheck", enable_shield_recheck_default)),
    )
    st.session_state["enable_shield_recheck"] = enable_shield_recheck
    show_shield_intermediate = st.sidebar.checkbox(
        "Show Shield Intermediate",
        value=bool(st.session_state.get("show_shield_intermediate", False)),
    )
    st.session_state["show_shield_intermediate"] = show_shield_intermediate

    st.sidebar.header("社会语境干扰")
    mode_label_to_key = {
        "NONE": InterferenceMode.NONE.value,
        "Correct Guidance": InterferenceMode.CORRECT_GUIDANCE.value,
        "Wrong Guidance": InterferenceMode.WRONG_GUIDANCE.value,
    }
    selected_mode_label = st.sidebar.selectbox(
        "干扰方式",
        options=list(mode_label_to_key.keys()),
        index=0,
    )
    selected_mode = InterferenceMode(mode_label_to_key[selected_mode_label])

    slider_label = "主阵营人数 / 6"
    if selected_mode == InterferenceMode.CORRECT_GUIDANCE:
        slider_label = "正确派人数 / 6"
    elif selected_mode == InterferenceMode.WRONG_GUIDANCE:
        slider_label = "错误派人数 / 6"

    majority_size = st.sidebar.slider(
        slider_label,
        min_value=0,
        max_value=6,
        value=4,
        disabled=(selected_mode == InterferenceMode.NONE),
    )
    if selected_mode == InterferenceMode.CORRECT_GUIDANCE:
        st.sidebar.caption(f"错误派人数 = {6 - majority_size}")
    elif selected_mode == InterferenceMode.WRONG_GUIDANCE:
        st.sidebar.caption(f"正确派人数 = {6 - majority_size}")

    reroll_clicked = st.sidebar.button("重新随机生成句式")
    seed = _sync_interference_seed(
        mode_key=selected_mode.value,
        majority_size=majority_size,
        reroll=reroll_clicked,
    )
    st.sidebar.caption(f"Interference seed: {seed}")

    text_input = st.text_area("输入文本", value=preset_text, height=200)
    uploaded = st.file_uploader("可选上传图像", type=["png", "jpg", "jpeg"])
    image_bytes = _read_image_bytes(uploaded) or preset_image_bytes

    effective_mode = selected_mode
    guidance_result = None
    final_prompt = text_input
    interference_summary = {
        "mode": effective_mode.value,
        "majority_size": 0,
        "minority_size": 0,
        "majority_choice": "N/A",
        "minority_choice": "N/A",
        "majority_roles": [],
    }

    if selected_mode != InterferenceMode.NONE:
        can_apply = bool(use_dataset and selected_sample and selected_sample.answer)
        if not can_apply:
            st.warning("手动输入模式缺少标准答案，Correct/Wrong Guidance 已禁用并回退到 NONE。")
            effective_mode = InterferenceMode.NONE
        else:
            try:
                roles = load_roles_config(Path("data") / "guidance_roles.json")
                rng = random.Random(seed)
                guidance_result = build_guidance_prompt(
                    base_prompt=text_input,
                    mode=selected_mode,
                    majority_size=majority_size,
                    roles=roles,
                    correct_choice_letter=selected_sample.answer,
                    options=selected_sample.options,
                    rng=rng,
                )
                final_prompt = guidance_result.full_prompt
                interference_summary = {
                    "mode": guidance_result.mode.value,
                    "majority_size": guidance_result.majority_size,
                    "minority_size": 6 - guidance_result.majority_size,
                    "majority_choice": guidance_result.majority_choice_text,
                    "minority_choice": guidance_result.minority_choice_text,
                    "majority_roles": guidance_result.majority_roles,
                }
            except Exception as exc:
                st.warning(f"干扰生成失败，已回退到 NONE：{exc}")
                effective_mode = InterferenceMode.NONE

    if effective_mode == InterferenceMode.NONE and guidance_result is None:
        final_prompt = text_input
        interference_summary["mode"] = InterferenceMode.NONE.value

    st.subheader("Final Prompt")
    st.code(final_prompt, language="text")
    st.subheader("Interference Summary")
    st.json(interference_summary)

    if st.button("Run"):
        run_text = text_input if effective_mode == InterferenceMode.NONE else final_prompt
        query = normalize_input(run_text, image_bytes)

        target_config = None
        if enable_target_config:
            if target_api_key.strip() and target_base_url.strip() and target_model_name.strip():
                target_config = TargetModelConfig(
                    api_key=target_api_key.strip(),
                    base_url=target_base_url.strip(),
                    model_name=target_model_name.strip(),
                )
            else:
                st.warning("Target配置未填写完整，已回退为默认回答模型配置。")

        run_solver = GeoSolver(
            model_name=model_name,
            vision_model=vision_model,
            target_config=target_config,
            enable_recheck=enable_shield_recheck,
        )
        run_system = GeoShieldSystem(router=router, solver=run_solver)
        result = run_system.run(query)

        route = result["route"]
        st.subheader("路由输出")
        st.json({"layer": route.layer, "risk": route.risk, "reason": route.reason})

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Baseline")
            st.write(result["baseline"].answer)
        with col2:
            st.subheader("Ours")
            if result["defended"]:
                st.write(result["defended"].answer)
            else:
                st.write("(LOW risk: using baseline)")

        if show_shield_intermediate:
            with st.expander("Shield Intermediate", expanded=False):
                if result["defended"]:
                    trace = getattr(run_solver, "last_defended_trace", {})
                    st.json(
                        {
                            "persona_answer": trace.get("persona_answer"),
                            "final_answer": trace.get("final_answer"),
                            "recheck_enabled": trace.get("recheck_enabled"),
                        }
                    )
                else:
                    st.write("No shield intermediate because risk is LOW.")

        if image_bytes:
            st.image(image_bytes, caption="Input Image", width=700)


if __name__ == "__main__":
    main()
