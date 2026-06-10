
# Product Main Image Agent (电商主图生成智能体)
基于 AI Agent 框架的电商产品主图自动生成工具。输入产品信息和白底产品图，自动完成卖点分析、主图策划、提示词生成、图片生成和保存，一站式输出 5 张不同风格的电商主图。

## 效果流程

```
┌─ 输入 ─────────────────────────────────────┐
│  产品信息.txt  +  白底产品图                 │
└────────────────┬────────────────────────────┘
                 ▼
┌─ AI 分析 ───────────────────────────────────┐
│  提取核心卖点 → 用户确认 → 生成5张策划方案    │
└────────────────┬────────────────────────────┘
                 ▼
┌─ 参数收集 ──────────────────────────────────┐
│  选择比例/平台（淘宝/京东/抖音/小红书等）      │
└────────────────┬────────────────────────────┘
                 ▼
┌─ 图片生成 ──────────────────────────────────┐
│  白底图上床 → 生成提示词(含价格) → 5次API调用 │
│  每次调用传入白底图作为参考，保持主体一致       │
└────────────────┬────────────────────────────┘
                 ▼
┌─ 输出 ─────────────────────────────────────┐
│  5张电商主图保存到本地 → 询问满意度           │
│  不满意 → 修改提示词重新生成                  │
└────────────────────────────────────────────┘
```

## 核心特性

- **主体保持一致** — 上传白底产品图作为参考，AI 生成的所有图片中产品主体形状和外观不变，仅改变背景、场景、构图和风格
- **价格信息自动提取** — 从产品信息文件中自动识别价格，注入生成提示词，最终图片带价格标签展示
- **5 张不同风格** — 每轮生成 5 张不同主题/构图/场景的电商主图
- **分开独立调用** — 每张图独立调用豆包 Seedream API，确保每张图质量
- **多平台适配** — 支持淘宝/京东/拼多多(1:1)、抖音(1:1)、小红书(3:4) 等平台比例
- **迭代修改** — 生成不满意可随时反馈，Agent 自动调整提示词重新生成

## 技术栈

| 组件 | 选型 |
|---|---|
| AI Agent 框架 | [deepagents](https://github.com/langchain-ai/deepagents) (langchain) |
| 大语言模型 | 豆包 doubao-seed-2-0-lite (通过火山引擎 Ark API) |
| 图片生成模型 | 豆包 doubao-seedream-4-0-250828 (通过火山引擎 Ark API) |
| 图床服务 | freeimage.host (公开免费) |
| Python SDK | openai, langchain-openai |

## 快速开始

### 前置条件

- Python 3.10+
- [火山引擎 Ark](https://console.volcengine.com/ark) API Key（开通豆包 Seedream 模型和 LLM 模型）
- freeimage.host API Key（可选，使用默认公开 Key）

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/product-main-image-agent.git
cd product-main-image-agent

# 安装依赖
pip install langchain langchain_openai deepagents python-dotenv requests openai
```

### 配置

将 `.env` 文件中的配置替换为自己的 API Key：

```env
DOUBAO_API_KEY=你的火山引擎ARK_API_KEY
LLM_MODEL=doubao-seed-2-0-lite-260428
LLM_API_URL=https://ark.cn-beijing.volces.com/api/v3/
SEEDANCE_API_URL=https://ark.cn-beijing.volces.com/api/v3/images/generations
IMAGE_HOSTING_API_URL=https://freeimage.host/api/1/upload
IMAGE_HOSTING_API_KEY=你的免费图片托管API密钥
```

### 运行

```bash
python zhutuagent.py
```

启动后按提示输入：
1. 产品信息文件路径（txt 格式，含产品名称、规格、价格等）
2. 白底产品图路径（去背景的产品图）
3. 确认卖点分析结果
4. 选择图片比例或目标平台

Agent 会自动完成后续所有步骤。

## 项目结构

```
product-main-image-agent/
├── zhutuagent.py                   # 主智能体实现
├── .env                            # 环境变量配置
├── product_main_image_agent_plan.md # 设计文档
├── input_files/                    # 输入文件目录
│   ├── 产品信息.txt                # 产品信息文件
│   └── 白底图.png                  # 白底产品图
└── output_images/                  # 输出图片目录
    ├── main_image_1.png
    ├── main_image_2.png
    ├── main_image_3.png
    ├── main_image_4.png
    └── main_image_5.png
```

## 核心 API 参数

豆包 Seedream 4.0 图生图的关键参数：

| 参数 | 值 | 说明 |
|---|---|---|
| `model` | `doubao-seedream-4-0-250828` | 模型名称 |
| `image` | 白底产品图的公开 URL | **注意**：参数名为 `image` 而非 `image_url` |
| `prompt` | AI 生成的提示词 | 含场景、背景、光线、构图、价格展示描述 |
| `size` | `2K` | 输出分辨率 |
| `sequential_image_generation` | `"disabled"` | 禁用批量顺序生成 |
| `watermark` | `true` | 添加水印 |

## 价格信息传递链路

```
产品信息.txt (含价格)
  → read_product_info() 读取完整内容
    → analyze_selling_points() 提取卖点
      → generate_image_plans() 生成策划方案
        → generate_image_prompts(plans, ratio, image_url, product_info)
            ↑ 自动提取含"价格/售价/元/¥"等关键词的行
            ↓ 价格信息注入提示词（要求画面显示价格标签）
          → generate_images(prompts, reference_image_url)
            → 生成带价格标签的主图
```

## 工具函数一览

| 工具 | 功能 | 输入 |
|---|---|---|
| `read_product_info` | 读取产品信息文件 | `file_path` |
| `upload_to_image_hosting` | 上传白底图到图床 | `local_path` |
| `analyze_selling_points` | 提取产品核心卖点 | `product_info` |
| `generate_image_plans` | 生成 5 张主图策划方案 | `selling_points` |
| `generate_image_prompts` | 生成 AI 绘画提示词（含价格） | `plans`, `ratio`, `image_url`, `product_info` |
| `generate_images` | 调用 Seedream 生成 5 张图 | `prompts`, `reference_image_url` |
| `save_images` | 保存图片到本地 | `image_urls`, `output_dir` |

## License

MIT
