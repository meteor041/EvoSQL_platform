# EvoSQL Platform

校园智慧问数平台 Demo 优先版实现。当前版本包含：

- BIRD 数据集加载与 smoke runner
- EvoSQL 最小闭环引擎（MLICR / SCR / ECA / fallback）
- SQLite 只读沙箱执行与 SQL 安全拦截
- 校园脱敏合成库、元数据与问答集
- FastAPI 问数服务、会话追问、审计日志接口
- Vue 3 + Vite 前端骨架

## Backend

推荐直接在仓库根目录运行：

```bash
python scripts/run_dev.py
```

这个脚本会先检查本机可绑定的地址和端口，再启动 `uvicorn`，避免 Windows 上常见的 `WinError 10013`。

可选环境变量：

```bash
set HOST=127.0.0.1
set PORT=8001
set RELOAD=1
python scripts/run_dev.py
```

兼容旧方式，但如果默认端口被系统拒绝，仍可能失败：

```bash
set PYTHONPATH=src
python -m uvicorn evosql_platform.app.main:app --reload --host 127.0.0.1 --port 8001
```

## Optional Install

```bash
pip install -e .
```

## Tests

```bash
set PYTHONPATH=src
pytest
```

## Smoke Run

```bash
python smoke.py
```

## LLM Mode

校园查询默认按 `CAMPUS_LLM_MODE=auto` 运行：

```bash
set CAMPUS_LLM_MODE=auto
```

可选：

```bash
set CAMPUS_LLM_MODE=mock
```

强制走稳定的演示问答集。

```bash
set CAMPUS_LLM_MODE=qwen
set OPENROUTER_API_KEY=你的key
```

强制走真实 OpenRouter Qwen。

说明：
- `auto` / `qwen` 模式下，如果真实模型生成失败、被安全拦截、结果为空或输出明显异常，会自动回退到 mock 演示链路。
- 结果摘要也会优先走 Qwen，失败后回退为本地模板摘要。
