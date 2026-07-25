# LottoPilot 系统架构

## 1. 架构目标

- 单仓库、单应用镜像、单域名访问。
- 开发时前后端分离热更新，发布时前端静态文件合入后端镜像。
- 首版只包含应用和 PostgreSQL 两个容器。
- 模块边界清晰，后续可以平滑拆出 Worker 和 Redis。

## 2. 总体结构

```text
Browser
  │
  │ HTTPS / same origin
  ▼
LottoPilot container :8000
  ├── FastAPI REST API
  ├── React static files
  ├── authentication
  ├── data ingestion scheduler
  ├── statistics engine
  ├── recommendation engine
  ├── backtest engine
  └── OpenAI-compatible client
  │
  ▼
LottoPilot-postgres :5432
```

宝塔/Nginx 只负责域名、TLS 和反向代理到宿主机 `127.0.0.1:8088`。

## 3. 推荐仓库结构

```text
LottoPilot/
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── migrations/
│   ├── tests/
│   └── lottopilot/
│       ├── main.py
│       ├── api/
│       │   ├── deps.py
│       │   └── v1/
│       ├── core/
│       │   ├── config.py
│       │   ├── logging.py
│       │   ├── security.py
│       │   └── errors.py
│       ├── db/
│       │   ├── base.py
│       │   ├── session.py
│       │   └── models/
│       ├── schemas/
│       ├── repositories/
│       ├── services/
│       ├── ingestion/
│       │   ├── base.py
│       │   ├── ssq.py
│       │   ├── dlt.py
│       │   ├── validators.py
│       │   └── imports.py
│       ├── analytics/
│       │   ├── features.py
│       │   ├── distributions.py
│       │   └── snapshots.py
│       ├── recommendation/
│       │   ├── candidates.py
│       │   ├── scoring.py
│       │   ├── diversity.py
│       │   └── engine.py
│       ├── backtest/
│       │   ├── walk_forward.py
│       │   ├── metrics.py
│       │   └── runner.py
│       ├── ai/
│       │   ├── client.py
│       │   ├── prompts.py
│       │   ├── schemas.py
│       │   └── reranker.py
│       ├── scheduler/
│       └── static/
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   └── src/
│       ├── api/
│       ├── components/
│       ├── features/
│       ├── pages/
│       ├── routes/
│       ├── stores/
│       ├── styles/
│       └── types/
├── deploy/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   └── .env.example
├── .github/workflows/
├── docs/
├── AGENTS.md
├── README.md
└── LICENSE
```

## 4. 后端分层

### API 层

只负责协议转换：认证、参数校验、调用 service、映射响应和错误码。API 层不得包含统计公式、SQL 拼接和第三方数据解析。

### Service 层

编排业务用例，例如“同步开奖”“生成推荐”“运行回测”“测试 AI 连接”。事务边界在 service 层定义。

### Repository 层

封装数据库查询和持久化。所有列表接口必须在数据库层分页；禁止先加载全部记录再在 Python 中分页。

### Domain/Engine 层

`analytics`、`recommendation`、`backtest` 尽量写成纯函数或显式输入输出对象，避免依赖 FastAPI 和全局数据库连接，便于测试和离线运行。

### Integration 层

`ingestion` 和 `ai` 隔离外部接口变化。官方字段改变或 AI 服务商变化时，核心算法代码保持稳定。

## 5. 前端架构

- React Router 7 负责页面路由。
- TanStack Query 管理服务端数据、缓存和请求状态。
- Zustand 只存认证摘要、主题、彩种选择等客户端状态。
- `features/<feature>` 放业务组件、hooks、types 和 API 封装。
- `components/ui` 放无业务含义的基础组件。
- 所有金额、日期、号码格式化通过统一 utility，不在页面重复实现。

## 6. 运行模式

### 开发模式

```text
frontend Vite :5173
  └── proxy /api -> backend :8000
backend FastAPI :8000
postgres :5432
```

### 生产模式

1. Node 阶段执行前端测试和 `npm run build`。
2. 将 `frontend/dist` 复制到 Python 镜像中的 `lottopilot/static`。
3. FastAPI 提供 `/assets/*` 和 SPA fallback。
4. `/api/*`、`/health` 等接口路由不进入 SPA fallback。

## 7. 调度和并发

- 首版使用单应用实例和单 Uvicorn worker。
- APScheduler 在应用 lifespan 中启动和关闭。
- 所有定时任务使用 PostgreSQL advisory lock，防止误启动两个实例时重复执行。
- CPU 密集的候选生成和回测通过 `ProcessPoolExecutor` 执行，任务状态写入数据库。
- 后续需要多实例或独立 Worker 时，再引入 Redis 与任务队列。

## 8. 关键数据流

### 开奖同步

```text
Scheduler/API -> Source Adapter -> Raw Payload -> Parser -> Validator
              -> Upsert Draw -> Ingestion Log -> Refresh Statistics Snapshot
```

### 推荐生成

```text
Validated Draws -> Feature Snapshot -> Candidate Generator
                -> Statistical Scorer -> Diversity Selector
                -> Optional AI Reranker/Explanation
                -> Persist Run + 5 Tickets -> API Response
```

### 滚动回测

```text
For each historical target issue:
  use draws strictly before target
  -> build features
  -> generate 5 tickets
  -> compare with target result
  -> compare with seeded random baseline
  -> aggregate metrics
```

## 9. 可观测性

- 日志使用 JSON 格式，字段至少包含 `timestamp`、`level`、`request_id`、`event`、`lottery_type`、`issue`。
- 禁止记录 AI API Key、密码、完整 session token。
- `/health` 只检查进程；`/api/v1/system/ready` 检查数据库和迁移版本。
- 重要任务记录开始时间、结束时间、状态、错误摘要和处理数量。
