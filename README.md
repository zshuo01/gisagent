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

## 7. 前端使用说明

以下说明对应 `app.py` 当前页面中的控件与展示区域。

### 7.1 题目来源

- `从data加载题目`（复选框）
  - 开启：从 `data/` 下的 JSON 样本加载题目，自动填充题面文本，若样本有图片路径会自动加载图片。
  - 关闭：使用手动输入模式，题目由 `输入文本` 文本框提供。
- `data目录`（输入框）
  - 指定数据集目录，默认 `data`。
- `选择题目`（下拉框，仅数据集模式显示）
  - 选择具体样本；侧边栏会显示该样本 `Gold` 与 `Tag`。

### 7.2 社会语境干扰控件

- `干扰方式`（下拉）
  - `NONE`：关闭干扰，系统按原始题面流程运行。
  - `Correct Guidance`：6名角色中主阵营指向正确选项，另一阵营指向同一个错误选项。
  - `Wrong Guidance`：6名角色中主阵营指向同一个错误选项，另一阵营指向正确选项。
- `MAJORITY_SIZE`（滑条，文案会随模式变化）
  - 在 `Correct Guidance` 下表示“正确派人数 / 6”。
  - 在 `Wrong Guidance` 下表示“错误派人数 / 6”。
  - 另一阵营人数始终为 `6 - MAJORITY_SIZE`。
- `重新随机生成句式`（按钮）
  - 每次点击会重新随机：主阵营角色分配、每个角色句式模板、错误选项字母。
- `Final Prompt`（展示区）
  - 展示本次最终发送给系统的完整提示词（包括题面和6位角色发言）。
- `Interference Summary`（展示区）
  - 展示本次干扰摘要：模式、两派人数、两派选项、主阵营角色列表。

### 7.3 被测试模型配置区

- `启用前端Target配置`（复选框）
  - 关闭（默认）：Baseline/Ours 使用系统默认配置（环境变量或代码默认值）。
  - 开启：使用你在前端填写的目标模型参数进行 Baseline/Ours 生成。
- `Target API Key`、`Target Base URL`、`Target Model Name`（输入框）
  - 三项需要完整填写才生效；未填完整会自动回退默认配置。
- 注意
  - 该区域只影响被测试模型（Baseline/Ours）。
  - Router 使用支撑模型配置，不受此区域影响。

### 7.4 Shield 控件

- `启用Shield二次复核(开启后使用Persona→Recheck)`（复选框）
  - 仅在 `risk=HIGH` 时生效。
  - 关闭：使用单阶段 Shield 提示词。
  - 开启：使用两阶段流程（Persona 先答，再 Recheck 复核）。
- `Show Shield Intermediate`（复选框）
  - 关闭（默认）：只显示 Baseline/Ours 主结果。
  - 开启：额外显示 Shield 中间信息（如 `persona_answer` 与 `final_answer`）。

### 7.5 运行按钮与输出

- `Run`（按钮）会触发以下流程：
  1. 组装输入（题面文本 + 可选图像 + 可选干扰 full_prompt）。
  2. Router 输出 `layer/risk/reason`。
  3. 生成 Baseline 结果。
  4. 若 `risk=HIGH`，生成 Ours（Shield）结果；若 `risk=LOW`，Ours 复用 Baseline。
- 页面输出包括：
  - `路由输出`（JSON）
  - `Baseline` 与 `Ours` 对比结果
  - 输入图像预览（若存在）

### 7.6 默认行为与回退方式（回到稳定流程）

如需回到原稳定流程，建议保持以下配置：

1. `干扰方式 = NONE`
2. `启用前端Target配置 = 关闭`
3. `启用Shield二次复核 = 关闭`
4. `Show Shield Intermediate = 关闭`

在以上配置下，系统会按默认路径运行，新增功能不介入核心流程。
