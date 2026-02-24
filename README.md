# 抗干扰地理空间智能协作系统 MVP

本项目是论文第5章（抗干扰地理空间智能协作系统）的最简可跑通MVP实现，遵循 Router-Controller-Solver 架构，提供 Streamlit 前端对比 Baseline 与 Ours（防御增强）输出，并包含最小评测脚本。

## 1. 安装

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. 配置

复制 `.env.example` 为 `.env` 并填写 API Key 与模型名：

```bash
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-4o-mini
VISION_MODEL=gpt-4o-mini
```

## 3. 运行前端

```bash
python -m streamlit run app.py
```

## 4. 数据集说明

将数据集 JSON 与图片放在 `data/` 目录下（可递归）。JSON 格式示例：

```json
{
  "question_set": {
    "title": "...",
    "image": "image_xxx.png",
    "questions": [
      {
        "id": 4,
        "question": "...（   ）",
        "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
        "answer": "A",
        "tag": "C3"
      }
    ]
  }
}
```

## 5. 评测（第5.4节最小鲁棒性对比）

```bash
python eval/run_eval.py
```

输出会打印 `sample_id / tag / risk / gold / base_pred / ours_pred` 并汇总准确率。

## 6. 目录结构

```
.
├─ app.py
├─ core/
│  ├─ __init__.py
│  ├─ dataset.py
│  ├─ mm_processor.py
│  ├─ prompts.py
│  ├─ router.py
│  ├─ schemas.py
│  ├─ shield.py
│  └─ solver.py
├─ eval/
│  ├─ __init__.py
│  └─ run_eval.py
├─ tests/
│  ├─ __init__.py
│  ├─ test_end_to_end.py
│  ├─ test_router.py
│  └─ test_shield.py
├─ data/
├─ requirements.txt
└─ .env.example
```

