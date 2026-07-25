# LottoPilot 验收标准（Acceptance Criteria）

> 版本：v1.3  
> 适用范围：当前仓库实现与后续迭代  
> 判定原则：每条必须可观察、可复现、可自动化或人工抽检。

---

## 0. 全局硬约束（任一失败即不通过）

| ID | 验收项 | 通过标准 | 验证方式 |
|---|---|---|---|
| G-01 | 产品边界 | 系统仅支持 `ssq` / `dlt`，不提供购彩下单 | 代码检索 + UI 文案抽检 |
| G-02 | 免责声明 | 所有推荐/回测结果标注“模型评分/历史分析，不承诺中奖” | UI 抽检 + API 字段抽检 |
| G-03 | 统一响应信封 | API 返回 `{success,data,error,request_id}`，并带 `X-Request-ID` | `/health` 与业务接口抽检 |
| G-04 | 命名约束 | 产品名 `LottoPilot`，包/镜像 `lottopilot`，容器 `LottoPilot`/`LottoPilot-postgres` | compose/Dockerfile 检查 |
| G-05 | AI 权重上限 | AI 对最终分贡献 ≤ 10%；失败时回退纯统计 | `scripts/run_unit_offline.py` + 代码审查 |
| G-06 | 无未来泄漏 | 回测与推荐特征只使用 cutoff 之前数据 | `backtest_core` offline unit + 代码审查 |

---

## 1. Phase 0 工程骨架

| ID | 验收项 | 通过标准 |
|---|---|---|
| P0-01 | 仓库结构 | 存在 `backend/`、`frontend/`、`docs/`、`deploy/`、`scripts/`、`docker-compose.yml`、`Dockerfile` |
| P0-02 | 配置样例 | 存在 `.env.example`，含 DB/会话/端口/时区关键项 |
| P0-03 | 后端可导入 | `app.main:create_app()` 可创建 FastAPI 应用（有依赖时） |
| P0-04 | 前端可构建目录 | `frontend/src` 含路由、页面、API 客户端 |
| P0-05 | CI 定义 | `.github/workflows/ci.yml` 定义 backend/frontend/docker 任务 |
| P0-06 | 健康检查 | `GET /health` 返回 success 信封与 `status=ok` |

**完成定义：** P0-01~P0-06 全通过。

---

## 2. Phase 1 初始化与认证

| ID | 验收项 | 通过标准 |
|---|---|---|
| P1-01 | Setup 状态 | `GET /api/v1/setup/status` 正确反映是否已初始化 |
| P1-02 | 首次 Setup | 未初始化时可 `POST /api/v1/setup` 创建管理员并写 session cookie |
| P1-03 | 防重复 Setup | 已初始化后再次 setup 返回 `SETUP_ALREADY_COMPLETED` |
| P1-04 | 登录登出 | login 设置 HttpOnly cookie；logout 撤销会话 |
| P1-05 | 当前用户 | 登录后 `GET /api/v1/auth/me` 返回用户；未登录 401 |
| P1-06 | 前端向导 | 未初始化进入 `/setup`；已初始化未登录进入 `/login` |
| P1-07 | 审计日志 | setup/login/logout 及关键配置变更写入 `audit_logs`；`GET /audit-logs` 可分页 |

**完成定义：** P1-01~P1-07 全通过。

---

## 3. Phase 2 开奖数据

| ID | 验收项 | 通过标准 |
|---|---|---|
| P2-01 | 号码校验 | 非法数量/范围/重复号码被拒绝 |
| P2-02 | SSQ 解析 | 官方样例 JSON 可解析为合法规范化记录 |
| P2-03 | DLT 解析 | 官方样例 JSON 可解析为合法规范化记录 |
| P2-04 | Upsert 语义 | 同彩种同期：hash 相同 skip；不同 update；不存在 insert |
| P2-05 | 同步 API | 登录后 `POST /api/v1/draws/sync` 返回 202 与 job/run id |
| P2-06 | 查询 API | `GET /draws`、`/draws/latest`、`/draws/{type}/{issue}` 可用 |
| P2-07 | CSV 导入 | preview 区分 valid/invalid；commit 可入库统计 |
| P2-08 | 前端开奖页 | 可切换彩种、触发同步、查看列表与最近任务 |
| P2-09 | CSV 导入 UI | 开奖页可上传 CSV 预览 valid/invalid，并可提交有效行 |
| P2-10 | CSV 预览纯测 | valid/invalid 统计可被 offline unit 复现 |

**完成定义：** P2-01~P2-10 全通过。

---

## 4. Phase 3 统计分析

| ID | 验收项 | 通过标准 |
|---|---|---|
| P3-01 | 频率 | 给定样例，号码频次正确 |
| P3-02 | 遗漏 | 当前遗漏（newest-first）计算正确 |
| P3-03 | 和值/跨度/奇偶 | 可输出每期结构特征 |
| P3-04 | 热冷号 | 指定窗口返回 hot/cold |
| P3-05 | 概览 API | `GET /api/v1/analytics/overview` 返回完整结构 |
| P3-06 | 前端统计页 | 可切换彩种/窗口并展示频率遗漏共现 |
| P3-07 | 规格别名 | `GET /analytics/numbers` 与 `/distributions` 可用 |
| P3-08 | 分区 UI | 统计页展示分区分布（zone_low/mid/high） |

**完成定义：** P3-01~P3-08 全通过。

---

## 5. Phase 4 推荐引擎

| ID | 验收项 | 通过标准 |
|---|---|---|
| P4-01 | 历史门槛 | 历史 < 5 期时拒绝推荐并返回明确错误码 |
| P4-02 | 固定 5 注 | 成功时 `tickets.length === 5`，rank=1..5 |
| P4-03 | 合法性 | 每注通过双色球/大乐透规则校验 |
| P4-04 | 可复现 | 相同 lottery/target/strategy/seed/snapshot 生成相同候选集 |
| P4-05 | 元数据 | run 含 `seed`、`data_snapshot_hash`、`data_cutoff_issue`、`candidate_count` |
| P4-06 | 多样性 | 默认尽量限制主区过多重叠；必要时记录 relax level |
| P4-07 | API | `POST/GET /api/v1/recommendations` 可用 |
| P4-08 | 前端推荐页 | 可生成并展示 5 组号码、分数、解释与历史 |
| P4-09 | 开奖复盘 | 目标期开奖入库后可计算主/次区命中与奖级；支持手动 evaluate |
| P4-10 | 导出 | `GET /recommendations/{id}/export` 支持 json/csv |
| P4-11 | 解释重生成 | `POST /recommendations/{id}/explanations` 可刷新统计解释；前端可触发 |
| P4-12 | 票号复制 | TicketCard 可复制 主区 + 次区 文本 |
| P4-13 | 可复现 UI | 推荐页可输入 `seed` / `target_issue` 并在结果中展示 seed/snapshot |
| P4-14 | 首页 seed | 总览页生成推荐支持可选 seed 输入 |

**完成定义：** P4-01~P4-14 全通过。

---

## 6. Phase 5 回测

| ID | 验收项 | 通过标准 |
|---|---|---|
| P5-01 | 训练边界 | 目标期 i 仅使用 i 之前历史 |
| P5-02 | 范围校验 | start/end 期号必须存在且 start < end，训练窗口足够 |
| P5-03 | 基线对比 | 输出随机基线平均命中与策略命中 |
| P5-04 | 结果落库 | `backtest_runs` + `backtest_issue_results` 有数据 |
| P5-05 | API | `POST/GET /api/v1/backtests` 可用 |
| P5-06 | 前端回测页 | 可提交区间并展示 summary |
| P5-07 | 回测导出 | `GET /backtests/{id}/export` 支持 json/csv |
| P5-08 | 逐期结果 | `GET /backtests/{id}/issues` 可分页返回 |
| P5-09 | 前端逐期明细 | 回测页展示逐期命中与基线对比表 |
| P5-10 | 取消回测 API | `POST /backtests/{id}/cancel` 可将 queued/running 置为 cancelled |
| P5-11 | 取消回测 UI | 回测详情在 running/queued 时显示“取消回测”按钮 |

**完成定义：** P5-01~P5-11 全通过。

---

## 7. Phase 6 AI 集成

| ID | 验收项 | 通过标准 |
|---|---|---|
| P6-01 | Key 加密 | API Key 加密入库，列表接口仅返回脱敏 |
| P6-02 | 配置 CRUD | 可创建/更新 AI 配置，支持 default 标记 |
| P6-03 | 连通性测试 | `POST /settings/ai/{id}/test` 可返回 latency/status |
| P6-04 | 权重熔断 | AI 权重硬顶 0.10（offline unit） |
| P6-05 | 失败降级 | AI 不可用时推荐仍可纯统计完成（`ai_status=skipped/failed`） |
| P6-06 | 前端设置页 | 可保存配置并触发测试 |
| P6-07 | 删除/默认 | `DELETE /settings/ai/{id}`、`POST /settings/ai/{id}/set-default` 可用；被引用配置软删除 |

**完成定义：** P6-01~P6-07 全通过。AI 有限重排已接入推荐流水线：权重硬顶 0.10，失败时 `ai_status=failed/skipped` 且统计结果仍落库。

---

## 8. Phase 7/8 UI 与发布

| ID | 验收项 | 通过标准 |
|---|---|---|
| P7-01 | 页面齐全 | 总览/开奖/统计/推荐/回测/策略/设置 均可路由访问 |
| P7-02 | 响应式基础 | 桌面与窄屏导航可用（含手机底栏） |
| P7-03 | 公共组件 | 存在 `NumberBall`/`PageHeader`/`LotterySwitcher`/`EmptyState` 等基础组件 |
| P7-04 | 首页推荐核心 | 总览展示最近推荐 5 组与免责声明入口 |
| P7-05 | 亮/暗主题 | 顶栏可切换主题，偏好写入 localStorage，CSS tokens 支持 light/dark |
| P7-06 | 首页生成推荐 | 总览可直接生成 5 组候选并展示 TicketCard（复制/标签/解释） |
| P7-07 | 退出登录 | 顶栏退出调用 /auth/logout 并回到登录页 |
| P7-08 | 路由别名 | /history /data → 开奖；/analysis → 统计；/settings/ai|system → 设置 |
| P7-09 | 后台任务页 | `/jobs` 展示 `GET /system/jobs` 进度，支持自动刷新 |
| P7-10 | 加载/错误组件 | 存在 `LoadingState`/`ErrorState`，推荐/回测/任务/统计等页可复用 |
| P7-11 | 列表错误态 | 推荐页与回测页在 query 失败时展示可重试错误态 |
| P7-12 | 设置/策略错误态 | 设置页与策略页加载失败时展示可重试错误态 |
| P8-01 | Compose | 根目录 `docker-compose.yml` 定义双容器与健康检查 |
| P8-02 | Entrypoint | 启动时等待 DB 并执行 `alembic upgrade head` |
| P8-03 | 宝塔说明 | `deploy/baota/README.md` 给出反代、升级与备份步骤 |
| P8-04 | 备份恢复脚本 | 存在 `scripts/backup_pg.sh` / `scripts/restore_pg.sh` |
| P8-05 | Release Notes | 存在 `docs/RELEASE_NOTES_v1.0.0.md` |
| P8-06 | 多架构镜像流水线 | `.github/workflows/ci.yml` 定义 QEMU/Buildx 与 GHCR 推送 |
| P8-07 | 生产 Compose 样例 | `deploy/baota/docker-compose.yml` 可用预构建镜像启动 |
| P8-08 | 彩种目录 | `GET /lotteries` 返回 ssq/dlt 规则 |
| P8-09 | 策略 API | `GET/POST /strategies` 可用 |
| P8-10 | 定时同步 | `workers/scheduler.py` 可按 cron 触发增量同步（可关闭） |
| P8-11 | 系统设置 | `GET/PATCH /settings/system`；`ai_weight_cap` 不可超过 0.10 |
| P8-12 | 策略生命周期 | `PATCH` / `activate` / `set-default`；被引用版本 `STRATEGY_IMMUTABLE` |
| P8-13 | 策略前端 | `/strategies` 可创建实验版本、启用、设默认（含回测摘要） |
| P8-14 | 无 Docker 本地冒烟 | `scripts/local_api_smoke.py` 验证 health/OpenAPI/SPA（不依赖 Postgres） |
| P8-15 | SQLite 全流程 e2e | `scripts/local_sqlite_e2e.py` + `tests/integration/test_sqlite_e2e.py`：setup→CSV 导入→统计→策略→固定 seed 推荐 5 注（不依赖 Postgres/Docker） |
| P8-16 | API 人工清单自动化 | `local_sqlite_e2e` 覆盖 9.2 可 API 化项：login/logout、复盘/导出、回测 summary、策略 set-default、AI 脱敏 CRUD、系统设置与权重上限拒绝、audit/jobs、ready(database=ok) |
| P8-17 | Ready 分项语义 | `/system/ready` 将 DB ping 与 alembic_version 分离；缺迁移表时 database=ok、migrations=pending |
| P8-18 | 真实进程全栈冒烟 | `scripts/local_fullstack_smoke.py` 启动 uvicorn+SQLite，验证 SPA/cookie/导入/推荐（非 TestClient，可选） |
| P8-19 | GitHub Actions 门禁 | 单一工作流 `ci.yml`：offline + backend + frontend +（push 时）Docker 镜像推 GHCR |
| P8-20 | GHCR 镜像发布 | 同一 `CI` 工作流的 image job 多架构推送 `ghcr.io/<owner>/lottopilot`（main→edge，tag→latest/版本） |
| P8-21 | 服务器 Compose 部署 | 使用 `deploy/baota/docker-compose.yml` 拉取镜像 + Postgres，完成 Setup 与核心人工 9.2 |
| P7-13 | 主题单测 | `frontend/src/lib/theme-store.test.ts` 覆盖 localStorage 持久化与 toggle |
| P0-07 | Lifespan 启动 | 应用使用 FastAPI lifespan 管理调度器启停，而非废弃 on_event |

---

## 9. 质量门禁（合并前）

### 9.1 自动化

```bash
# offline (no third-party install required) — 最低本地门禁
python scripts/check_structure.py
python scripts/offline_acceptance.py
python scripts/run_unit_offline.py

# backend (需要依赖)
cd backend
pip install -e ".[dev]"
ruff check app tests
pytest -q

# frontend (需要依赖)
cd frontend
npm install
npm run build
npm test
```

**离线门禁通过标准：** 上述三个 offline 脚本均 exit 0。  
**本地 API 冒烟（无 Docker）：** `python scripts/local_api_smoke.py` → `LOCAL_API_SMOKE_OK`（需 backend venv 依赖；有 `frontend/dist` 时校验 SPA）。  
**完整门禁通过标准：** GitHub Actions `ci.yml` 全绿（offline + backend + frontend + docker build）。  
**镜像发布通过标准：** `ci.yml`（image job） 成功推送 GHCR。  
**生产通过标准：** 服务器 `docker compose` 健康 + 人工 9.2。

### 9.2 最低人工验收清单

见 `docs/MANUAL_ACCEPTANCE_CHECKLIST.md`。核心项：

1. 首次启动完成 setup，刷新后仍保持登录态。  
2. 同步或导入至少 20 期 SSQ/DLT 数据。  
3. 统计页能显示频率与遗漏。  
4. 生成推荐得到 5 组合法号码，页面有免责声明。  
5. 选择一段历史做回测，能看到相对基线指标。  
6. 在设置页保存 AI 配置，Key 不以明文回显；可设默认/删除。  
7. 系统设置可读取/修改且 AI 权重上限被校验。  
8. 策略页可创建实验版本并设默认（提供回测摘要）。  
9. 目标期开奖入库后，推荐页可手动复盘并看到命中；可导出 JSON/CSV。  
10. 按 `scripts/backup_pg.sh` 完成一次备份演练（有 Docker 时）。  
11. 推荐页/总览可填 seed，同 seed 生成结果可对照。  
12. 回测 running/queued 时可取消。  
13. 列表加载失败时可见 ErrorState 重试。  

---

## 10. 当前实现映射（便于对照）

| 能力 | 主要代码位置 |
|---|---|
| 应用入口 | `backend/app/main.py` |
| 认证/审计 | `backend/app/api/v1/auth.py`, `services/audit.py` |
| 开奖同步 | `backend/app/services/ingestion/*`, `api/v1/draws.py` |
| 统计 | `backend/app/services/analytics.py`, `api/v1/analytics.py` |
| 推荐 | `backend/app/services/recommendation/*`, `api/v1/recommendations.py` |
| 复盘/导出 | `backend/app/services/recommendation/evaluate.py`, `prize_rules.py` |
| 回测 | `backend/app/services/backtest.py`, `backtest_core.py`, `api/v1/backtests.py` |
| AI 配置 | `backend/app/services/ai/*`, `api/v1/settings.py` |
| 系统设置 | `backend/app/services/system_settings.py`, `api/v1/settings.py` |
| 策略 | `backend/app/api/v1/strategies.py`, `frontend/.../StrategiesPage.tsx` |
| 调度 | `backend/app/workers/scheduler.py` |
| 前端页面 | `frontend/src/features/*`（含 `jobs/JobsPage.tsx`） |
| 离线验收 | `scripts/check_structure.py`, `offline_acceptance.py`, `run_unit_offline.py` |
| 本地 SQLite e2e | `scripts/local_sqlite_e2e.py`, `backend/tests/integration/test_sqlite_e2e.py`, `backend/app/db/types.py` |
| 部署 | `Dockerfile`, `docker-compose.yml`, `deploy/baota/*`, `scripts/entrypoint.sh` |
| CI/CD | `.github/workflows/ci.yml` |
| Compose 静态校验 | `scripts/validate_compose_static.py` |

---

## 11. 发布判定

**MVP 可发布（统计版）条件：**

- G-01~G-06 通过  
- Phase 0~5 完成定义通过  
- Phase 6 的 P6-01/02/04/05/07 通过  
- 质量门禁 9.1 中 **GitHub Actions ci.yml 全绿**（含 offline/backend/frontend/docker build）  
- `ci.yml`（image job） 已产出可拉取的 GHCR 镜像  
- 服务器 Compose 健康检查通过  
- 人工清单 9.2 全勾选  

**完整版（含 AI 重排）额外条件：**

- 推荐流水线可调用 AI 解释/有限重排  
- AI 失败自动降级且审计字段完整  

**当前阶段说明（发布路径）：** 权威自动化证据以 **GitHub Actions** 为准；生产验收以 **服务器 Docker Compose 拉取 GHCR 镜像** + 人工清单 9.2 为准。本地 SQLite/全栈脚本仅作开发辅助，不是发布必选项。