# LottoPilot AI 开发总指南

本文件是交给任何 AI 编程代理、开发者或代码审查者的执行手册。它把产品、架构、数据、算法、API、前端、测试和发布文档串成一套实际工作流程。遇到局部实现问题时，先遵守本文件和 `project-spec.yaml` 的硬性约束，再参考对应领域文档。

## 1. 接手任务后的第一步

开始改代码前，按以下顺序读取：

1. `project-spec.yaml`：读取技术栈、运行端口、彩种规则和默认参数。
2. `README.md`：读取命名规则、文档导航和全局原则。
3. `AI_DEVELOPMENT_GUIDE.md`：读取本文件的开发流程和完成定义。
4. `PRODUCT.md`：确认用户场景、页面边界和验收标准。
5. `ARCHITECTURE.md`：确认模块边界、运行模式和目录结构。
6. 根据任务读取领域文档：
   - 开奖数据：`DATA_INGESTION.md`、`DATABASE.md`
   - 推荐和回测：`RECOMMENDATION_ENGINE.md`、`TESTING.md`
   - AI：`AI_INTEGRATION.md`、`API.md`
   - 页面：`FRONTEND.md`、`API.md`
   - 发布：`CI_CD_DEPLOYMENT.md`
   - 开发顺序：`ROADMAP.md`

然后检查当前工作树、已有实现、测试和环境文件。不能假设仓库是空的，也不能覆盖已有的用户修改。若代码与文档冲突，先判断代码是否已经形成稳定契约；需要改变契约时，先同步更新文档、schema、测试和迁移计划。

## 2. 项目身份和不可变约束

| 用途 | 固定值 |
|---|---|
| 产品展示名 | `LottoPilot` |
| GitHub 仓库展示名 | `LottoPilot` |
| Python 包 | `lottopilot` |
| Compose 服务 | `lottopilot`、`lottopilot-postgres` |
| 应用容器 | `LottoPilot` |
| 数据库容器 | `LottoPilot-postgres` |
| GHCR 镜像 | `ghcr.io/OWNER/lottopilot` |
| 后端端口 | 容器内 `8000`，默认宿主机 `8088` |
| 数据库 | PostgreSQL 17 |
| 首版容器数量 | 应用 + PostgreSQL |

必须保持以下全局事实：

- 产品支持双色球 `ssq` 和大乐透 `dlt`，每个彩种的号码范围以 `project-spec.yaml` 为唯一规则来源。
- 统计引擎决定候选的合法性、特征、统计分、去重和回测；AI 只做有限的二次排序、解释和摘要。
- 任意合法单注的理论中奖概率相同。界面和 API 使用“模型评分”“候选组合”“回测表现”等表述，不声称提高真实中奖概率或保证中奖。
- 推荐默认生成 5 组，必须合法、互不重复、可保存、可复现。
- 生成结果必须记录算法版本、策略版本、数据截止期、数据快照哈希和随机种子。
- 回测对每个目标期只能使用严格早于目标期的数据，禁止未来开奖数据泄漏。
- AI 调用失败、超时、限流或输出非法时，保留统计引擎结果并记录 AI 状态。
- AI 权重默认不超过最终分的 10%，不能让模型输出直接绕过号码规则校验。
- AI Key、数据库密码、session secret 和完整 Cookie 不得写入日志、响应、截图、测试快照或提交历史。
- 首版不依赖 Redis。只有在独立 Worker、多实例协调或高频缓存成为实际需求后才增加 Redis。
- 所有数据库结构变更必须通过 Alembic migration；禁止仅修改 ORM 模型而不写迁移。

## 3. 任务分类和代码落点

先把需求归类，再选择修改位置：

| 任务 | 首选位置 | 不应放置的位置 |
|---|---|---|
| HTTP 参数、认证、响应包装 | `backend/lottopilot/api/` | 算法模块、Repository |
| 用例编排和事务边界 | `backend/lottopilot/services/` | 路由函数、前端页面 |
| SQLAlchemy 查询和持久化 | `backend/lottopilot/repositories/` | API 路由、纯算法函数 |
| 开奖源请求和解析 | `backend/lottopilot/ingestion/` | 推荐引擎、页面组件 |
| 频率、遗漏、分布等特征 | `backend/lottopilot/analytics/` | 路由和 React 组件 |
| 候选、评分、去重、多样性 | `backend/lottopilot/recommendation/` | AI client、Repository |
| Walk-forward 回测 | `backend/lottopilot/backtest/` | API 路由中直接循环 |
| AI 请求、提示词、结构化结果 | `backend/lottopilot/ai/` | 前端直接调用供应商 |
| 页面业务和请求状态 | `frontend/src/features/`、`pages/` | `components/ui/` |
| 无业务含义的基础组件 | `frontend/src/components/ui/` | 业务 feature |
| 部署和镜像 | `deploy/`、`.github/workflows/` | 应用业务包 |

领域引擎尽量使用纯函数或显式输入输出对象，避免读取全局状态。外部系统差异必须被适配器隔离：官方开奖源变更不应迫使推荐算法改变，AI 供应商变更不应迫使前端改变。

## 4. 标准开发流程

每个功能按下面顺序完成，不要只修改其中一层：

1. **定义行为**：在对应文档中写清输入、输出、错误、权限、状态变化和验收标准。
2. **确认数据模型**：判断是否需要新表、新字段、索引、约束或审计记录。
3. **先写契约**：更新 Pydantic schema、TypeScript 类型/OpenAPI 约定和示例 JSON。
4. **实现领域逻辑**：先实现可测试的纯函数，再接 Repository 和 Service。
5. **实现 API**：路由只做认证、参数校验、调用 Service 和响应映射。
6. **实现前端**：接入 API client、加载/空/错误/成功状态，保证桌面和手机布局。
7. **补齐测试**：至少覆盖正常路径、边界条件、失败路径和权限边界。
8. **更新部署**：涉及环境变量、迁移、构建产物、定时任务或 Compose 时同步更新部署文档。
9. **运行质量门禁**：格式化、lint、类型检查、单元测试、集成测试、前端构建和 Docker smoke test。
10. **回顾文档**：检查文档示例、接口、端口、容器名和实际代码是否一致。

功能完成的最小交付物是：实现代码、迁移（如有）、测试、API/schema 变更、必要的页面状态、相关文档和验证结果。

## 5. 数据库变更流程

需要修改持久化结构时：

1. 在 `DATABASE.md` 增加字段、类型、约束、索引和迁移说明。
2. 创建 Alembic migration，保证空库 `upgrade head` 可执行。
3. 对已有大表采用“先 nullable、回填、再加约束”的多阶段发布方式。
4. 修改 ORM model、Repository、Pydantic schema 和 fixture。
5. 处理向后兼容：至少保证上一发布版本升级到当前版本时可完成迁移。
6. 对 secret 字段确认加密、脱敏、审计和删除行为。
7. 增加迁移测试、唯一性测试、边界校验和回滚说明。

核心数据规则：

- `draws` 使用 `(lottery_type, issue)` 幂等；重复同步只能更新可变元数据，不能产生重复开奖记录。
- 原始响应保存在 `raw_payload`，同时保存 `source_hash`、来源 URL 和采集时间。
- `recommendation_runs` 必须绑定 `data_cutoff_issue`、`data_snapshot_hash`、`seed` 和策略版本。
- 已被推荐运行引用的策略版本视为不可变；需要新实验时复制生成新版本。
- AI 配置只返回掩码 Key；任何审计 metadata 都不能包含密钥明文。

## 6. 开奖数据开发流程

每个数据源适配器都要实现统一接口，至少包含：抓取、解析、标准化、校验、来源信息和错误分类。处理链固定为：

```text
HTTP response -> raw payload -> parser -> normalized draw -> validator -> upsert
```

实现要求：

- 首选中国福利彩票发行管理中心和中国体育彩票官方数据。
- 使用低频请求、超时、限速、指数退避和响应缓存；不能通过并发请求绕过 WAF 或限流。
- 对页面字段、接口字段和日期格式做容错解析，但最终写库前必须严格校验。
- 双色球校验 6 个不重复红球 `1..33` 和 1 个蓝球 `1..16`。
- 大乐透校验 5 个不重复前区 `1..35` 和 2 个不重复后区 `1..12`。
- 同时校验期号、开奖日期、号码排序、范围、数量和重复记录。
- 官方源暂不可用时，不伪造数据；允许管理员通过 CSV/XLSX 预览后人工确认导入。
- 每次同步保存 run 状态、处理数量、跳过数量、错误摘要和失败原始项。

采集测试必须使用固定 fixture，不在单元测试中依赖实时网络。实时源只在手动集成测试或受控 smoke test 中访问。

## 7. 推荐引擎开发流程

推荐引擎的输入至少包含：彩种规则、历史开奖快照、目标期号、策略 profile、随机种子和 AI 开关。输出至少包含：5 组 ticket、每组号码、统计分、可选 AI 分、最终分、特征摘要、标签和解释。

处理顺序固定为：

1. 根据 cutoff 构造历史窗口和统计特征。
2. 按彩种规则生成合法候选池。
3. 计算频率、遗漏、时间衰减、和值、跨度、奇偶、大小、分区、连号和重复号等特征。
4. 计算统计分，并保留各项分解，禁止只返回一个无法解释的总分。
5. 过滤重复组合和明显违反硬约束的组合。
6. 使用贪心或明确的多样性算法选出 5 组。
7. 如启用 AI，发送压缩后的候选摘要，校验结构化响应并按权重上限融合。
8. 持久化完整运行元数据和 5 组结果。

可复现性要求：同一彩种、目标期号、策略版本、数据快照和 seed 必须产生相同结果。候选排序遇到分数相同必须使用稳定的确定性 tie-breaker，不能依赖数据库返回顺序或当前时间。

算法变更必须：

- 提升 `strategy_profile.version` 或算法版本标识。
- 更新黄金样本和回测基准。
- 运行无泄漏测试和随机 baseline 对比。
- 记录变更前后的指标，不因单次命中就宣称模型有效。
- 保持旧推荐记录可解释、可复盘、可重新读取。

## 8. AI 集成开发流程

AI 通过 OpenAI-compatible 协议调用，配置项为 `base_url`、`api_key` 和 `model`，可扩展 temperature、timeout 和 provider 标签。前端只调用 LottoPilot 后端，供应商 Key 永远不下发浏览器。

请求前：

- 只发送必要的聚合特征、候选摘要和任务指令。
- 不发送数据库密码、session、内部堆栈、原始 secret 或无关用户数据。
- 提示词明确要求 AI 不改变号码合法性，不输出真实概率保证。
- 设置超时、重试上限、响应长度和成本预算。

响应后：

- 先按 Pydantic/JSON Schema 校验，再使用任何字段。
- 校验 candidate ID、分数范围、解释长度和必填字段。
- AI 返回的号码只作为候选引用，最终号码必须重新通过统计引擎规则校验。
- 供应商错误、JSON 解析失败、schema 失败和超时分别记录状态，统计结果继续可用。
- 日志记录 provider、model、耗时、token/成本摘要和错误类别，不记录完整 prompt 中的 secret。

AI 的二次排序默认最多影响最终分的 10%。AI 不参与数据采集真值判断，不覆盖开奖数据，不直接写入 `draws`，也不执行任意 SQL 或系统命令。

## 9. API 开发流程

所有业务 API 使用 `/api/v1` 前缀、snake_case、统一 envelope 和 `X-Request-ID`。新增接口必须同时定义：

- HTTP 方法和路径
- 认证与权限
- 请求 schema
- 成功响应 schema
- 业务错误码和 HTTP 状态
- 分页、排序、过滤和幂等策略
- 是否创建后台 job
- 审计日志要求

推荐、同步和回测默认采用 job 模式，返回 `202 Accepted`、job ID 和资源 ID。列表必须在数据库层分页，不能把全部记录加载到 Python 后再分页。公开健康检查只检查进程；ready 检查数据库和 migration。

接口实现顺序：文档/API schema -> service 用例 -> repository -> route -> OpenAPI 检查 -> 前端调用 -> API 集成测试。API 路由中不能出现 SQL 拼接、第三方响应解析、统计公式或长时间循环。

## 10. 前端开发流程

页面必须围绕实际工作流：选择彩种、查看最新数据、查看 5 组候选、查看评分依据、触发同步、运行回测、管理 AI 配置。每个异步页面都要实现加载、空数据、错误、重试、成功和任务进行中状态。

前端约定：

- TanStack Query 管理服务端数据；Zustand 只管理认证摘要、主题和彩种选择等客户端状态。
- 业务代码放在 `features/`，通用无业务组件放在 `components/ui/`。
- 号码显示使用固定尺寸、稳定间距和统一格式化函数，避免动态内容造成布局抖动。
- 任何设置密钥的输入默认 password 类型；列表只显示掩码和最后测试状态。
- 桌面和手机都要检查无重叠、无溢出、无截断；操作反馈不能只依赖颜色。
- 前端不直接访问官方开奖源和 AI 供应商。
- 文案使用“候选”“模型评分”“历史回测”，不使用保证中奖或提高真实概率的表述。

## 11. 测试矩阵

| 层级 | 必测内容 |
|---|---|
| 纯函数单测 | 彩种规则、号码校验、特征、评分、去重、多样性、指标 |
| 属性测试 | 任意生成结果合法、排序稳定、重复输入幂等 |
| 采集测试 | fixture 解析、字段缺失、异常号码、WAF/超时、重复 upsert |
| 数据库测试 | migration、约束、索引查询、事务回滚、secret 脱敏 |
| API 集成 | 认证、权限、响应 envelope、错误码、分页、job 状态 |
| AI 测试 | mock provider、超时、非法 JSON、schema 失败、权重上限、降级 |
| 回测测试 | walk-forward、无未来数据、随机 baseline、固定 seed |
| 前端测试 | 组件状态、表单校验、任务轮询、移动端布局 |
| E2E | setup -> login -> sync/import -> recommend -> backtest -> export |
| 发布 smoke | Compose 启动、migration、`/health`、`/api/v1/system/ready`、SPA fallback |

推荐引擎测试必须包含固定黄金样本和随机基线。禁止只用“预测中了几次”作为唯一验收指标；至少记录命中分布、平均命中数、覆盖率、稳定性、运行耗时和与基线的比较。

## 12. 提交前检查清单

开始实现前：

- [ ] 已阅读本任务对应的领域文档。
- [ ] 已检查工作树，未覆盖他人修改。
- [ ] 已明确数据截止期、权限和失败行为。

实现完成后：

- [ ] 命名、端口、容器和环境变量与规格一致。
- [ ] 所有新数据库结构都有 Alembic migration。
- [ ] API 文档、schema、前端类型和实现一致。
- [ ] 号码合法性在入口和最终持久化前都经过校验。
- [ ] 推荐保存 seed、策略版本和快照哈希。
- [ ] 回测没有使用目标期或未来数据。
- [ ] AI 失败时统计结果仍能展示和落库。
- [ ] secret 没有出现在日志、响应、fixture 或 git diff。
- [ ] 已补充正常、边界和失败路径测试。
- [ ] 已运行格式化、lint、类型检查、测试、构建和 Docker smoke test。
- [ ] 已同步相关 docs，并在最终说明中列出未运行的检查。

## 13. 推荐命令

项目统一使用 uv 和 npm；目标工作流如下：

```bash
# 后端
cd backend
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy lottopilot
uv run pytest

# 前端
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test -- --run
npm run build

# 数据库和容器
docker compose -f deploy/docker-compose.yml config
docker compose -f deploy/docker-compose.yml up -d
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs --tail=200 lottopilot
```

若项目实际采用不同的包管理器或脚本名称，先更新本文档和 `CI_CD_DEPLOYMENT.md`，再让 CI 使用同一套命令。不要让本地命令、Actions 命令和 Docker 构建命令各自维护一套不一致的质量门禁。

## 14. 决策优先级

当需求含糊或文档之间出现冲突时，按以下优先级处理：

1. 用户明确要求且不违反已有数据完整性和产品边界的事项。
2. `project-spec.yaml` 的机器可读约束。
3. 本文件的全局开发规则。
4. 对应领域文档的详细契约。
5. 现有实现和测试所证明的稳定行为。
6. 最小、可回滚、可测试的实现方案。

任何新假设都要写入相关文档或决策记录。不要通过隐藏默认值、隐式全局状态、未记录的随机数或未测试的供应商行为解决不确定性。
