# Insight-mode

AI 洞察智能体：每日从 arXiv 抓取 AI 论文，经 LLM 分析提炼商业机会、技术方向、创新点，并通过邮件发送摘要。

## 当前实现范围

- **数据源**：仅 arXiv（cs.AI / cs.LG / cs.CL）
- **交付**：仅邮件推送

## 环境准备

1. Python 3.10+
2. 复制 `.env.example` 为 `.env`，填写：
   - `OPENAI_API_KEY`（必填，用于分析）
   - `OPENAI_BASE_URL`（可选，兼容国产大模型时修改）
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `EMAIL_TO`（邮件推送）

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env
```

## 运行

- **单次执行**（抓取 → 分析 → 邮件）：

```bash
python run_daily.py
```

- **定时执行**：用系统定时任务每日跑一次，例如：
  - Windows：任务计划程序，每日指定时间运行 `python c:\path\to\insight-mode\run_daily.py`
  - Linux/macOS：cron，例如 `0 8 * * * cd /path/to/insight-mode && python run_daily.py`
  - 或使用 GitHub Actions 在仓库内配置每日 workflow 调用

## 配置

- `config.yaml`：数据源、存储路径、分析模型与条数、交付插件列表等
- `.env`：API Key、SMTP 等敏感信息（勿提交版本库）

## 项目结构

- `src/storage.py`：RawStore、InsightStore（SQLite）
- `src/sources/arxiv.py`：arXiv 源适配器
- `src/fetcher.py`：抓取编排
- `src/analyzer.py`：LLM 洞察分析
- `src/delivery/`：交付层（热插拔）；当前仅 `plugins/email.py`
- `run_daily.py`：主入口

## 测试

```bash
python tests/test_storage.py
python tests/test_arxiv.py
python tests/test_fetcher.py
python tests/test_analyzer.py
```
