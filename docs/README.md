# LottoPilot 开发文档

> 本目录是 LottoPilot 的唯一开发规格入口。任何 AI 或开发者开始改代码前，先阅读本文件、`project-spec.yaml`、`ARCHITECTURE.md` 和 `AI_DEVELOPMENT_GUIDE.md`。

## 项目定位

LottoPilot 是一个面向双色球和大乐透的历史数据分析、候选号码生成、AI 辅助解释和滚动回测平台。系统输出的是“模型评分最高的 5 组候选组合”，不是对真实中奖概率的保证。

## 产品名称与技术标识

- 产品展示名：`LottoPilot`
- GitHub 仓库名：`LottoPilot`
- Python 包名：`lottopilot`
- Docker Compose 服务名：`lottopilot`
- 应用容器名：`LottoPilot`
- 数据库容器名：`LottoPilot-postgres`
- GHCR 镜像名：`ghcr.io/OWNER/lottopilot`

Docker/OCI 镜像仓库名按规范使用小写 `lottopilot`；这只是技术限制，不改变产品名称 LottoPilot。项目主标识始终使用 `LottoPilot`。

## 文档导航

| 文档 | 用途 |
|---|---|
| `project-spec.yaml` | 机器可读的全局约束、端口、服务、彩种规则和默认参数 |
| `PRODUCT.md` | 产品目标、用户流程、页面清单和验收标准 |
| `ARCHITECTURE.md` | 系统边界、模块划分、运行时和数据流 |
| `DATA_INGESTION.md` | 官方数据源、采集、校验、重试、补录和调度 |
| `DATABASE.md` | 数据库表、字段、索引和迁移规则 |
| `RECOMMENDATION_ENGINE.md` | 特征、候选生成、评分、多样性、回测和可复现性 |
| `AI_INTEGRATION.md` | AI Key 配置、OpenAI 兼容接口、提示词和输出校验 |
| `API.md` | HTTP API、认证、请求响应格式和错误码 |
| `FRONTEND.md` | 页面、组件、交互、主题、响应式和状态管理 |
| `TESTING.md` | 单元测试、集成测试、回测测试、端到端测试和质量门禁 |
| `CI_CD_DEPLOYMENT.md` | GitHub Actions、GHCR、Docker Compose、宝塔和升级回滚 |
| `ROADMAP.md` | 分阶段开发顺序和完成定义 |
| `AI_DEVELOPMENT_GUIDE.md` | AI 接手任务时的阅读顺序、改动流程和不可破坏约束 |

## 推荐阅读顺序

1. `project-spec.yaml`
2. `README.md`
3. `AI_DEVELOPMENT_GUIDE.md`
4. `PRODUCT.md`
5. `ARCHITECTURE.md`
6. `DATA_INGESTION.md`
7. `DATABASE.md`
8. `RECOMMENDATION_ENGINE.md`
9. `AI_INTEGRATION.md`
10. `API.md`
11. `FRONTEND.md`
12. `TESTING.md`
13. `CI_CD_DEPLOYMENT.md`
14. `ROADMAP.md`

## 全局开发原则

1. 先保证数据正确，再做模型复杂度。
2. 统计引擎负责合法组合、评分和回测；大模型负责解释、总结和有限范围的二次排序。
3. 所有推荐必须保存算法版本、特征窗口、随机种子、数据快照和 AI 配置摘要。
4. 任何历史回测都使用滚动时间切分，禁止把未来开奖数据泄露到训练特征。
5. 前端展示使用“模型评分”“回测表现”“候选组合”等词，不使用“必中”“真实中奖概率提升”等表述。
6. 首版只部署 `LottoPilot` 和 `LottoPilot-postgres` 两个容器，Redis 作为后续扩展项。
7. 每个新模块都要补充测试和对应文档；每个数据库变更都要有 Alembic migration。

## 验收标准

- [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md)：分阶段验收清单、质量门禁与发布判定。
- [ACCEPTANCE_STATUS.md](./ACCEPTANCE_STATUS.md)：当前实现对照状态与证据。

## 离线验收脚本

- python scripts/offline_acceptance.py：核心算法与解析验收
- python scripts/check_structure.py：目录/路由/命名结构验收

