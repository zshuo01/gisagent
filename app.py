import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from core.mm_processor import normalize_input
from core.router import TaskRouter
from core.solver import GeoSolver
from core.shield import GeoShieldSystem
from core.dataset import load_dataset, format_mcq_prompt


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


def main() -> None:
    st.title("抗干扰地理空间智能协作系统 MVP")

    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    vision_model = os.getenv("VISION_MODEL", model_name)

    router = TaskRouter(model_name=model_name)
    solver = GeoSolver(model_name=model_name, vision_model=vision_model)
    system = GeoShieldSystem(router=router, solver=solver)

    st.sidebar.header("数据集加载")
    data_dir = st.sidebar.text_input("data目录", value="data")
    use_dataset = st.sidebar.checkbox("从data加载题目", value=False)

    preset_text = ""
    preset_image_bytes = None

    if use_dataset:
        samples = load_dataset(data_dir)
        sample_options = [s.sample_id for s in samples]
        if sample_options:
            selected = st.sidebar.selectbox("选择题目", sample_options)
            sample = next(s for s in samples if s.sample_id == selected)
            preset_text = format_mcq_prompt(sample)
            preset_image_bytes = _read_path_bytes(sample.image_path)
            st.sidebar.write(f"Gold: {sample.answer} | Tag: {sample.tag}")
        else:
            st.sidebar.warning("data目录下未找到样本")

    text_input = st.text_area("输入文本", value=preset_text, height=200)
    uploaded = st.file_uploader("可选上传图像", type=["png", "jpg", "jpeg"])
    image_bytes = _read_image_bytes(uploaded) or preset_image_bytes

    if st.button("Run"):
        query = normalize_input(text_input, image_bytes)
        result = system.run(query)

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

        if image_bytes:
            st.image(image_bytes, caption="Input Image", use_column_width=True)


if __name__ == "__main__":
    main()
