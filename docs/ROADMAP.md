# LottoPilot 开发路线图

## Phase 0：工程骨架

- 创建 monorepo 目录。
- 初始化 FastAPI、React/Vite、PostgreSQL、Alembic。
- 固定 uv、npm、React Router 7 和 UUID v7 工程约定。
- 配置 Ruff、Mypy、Pytest、ESLint、Vitest。
- 实现统一 API envelope、配置、日志和健康检查。
- 创建 Dockerfile、Compose 和基础 Actions。

完成标志：空系统可以通过 Docker Compose 启动，前端能访问 `/health`。

## Phase 1：初始化和认证

- Setup Wizard。
- 管理员账号和 Argon2id 密码。
- Cookie session、登录、退出、当前用户。
- `user_sessions` 服务端会话和统一 `jobs` 后台任务表。
- 系统设置和审计日志。

完成标志：新环境完成初始化后进入受保护首页。

## Phase 2：官方开奖数据

- `draws`、`ingestion_runs`、`ingestion_errors` migration。
- 双色球官方适配器。
- 大乐透官方适配器。
- 全量/增量同步、限速、退避和锁。
- CSV/XLSX 导入预览与提交。
- 历史开奖和数据管理页面。

完成标志：两个彩种都能从官方源同步并通过校验，重复执行保持幂等。

## Phase 3：统计分析

- 多窗口频率、遗漏和时间衰减。
- 和值、跨度、奇偶、大小、分区、连号和重复号。
- 统计 API 和图表页面。
- 特征黄金样本测试。

完成标志：指定 cutoff 和窗口可稳定复现统计结果。

## Phase 4：推荐引擎

- 策略版本表。
- 候选生成、评分、去重和多样性选择。
- 固定 seed 和快照哈希。
- 推荐运行、5 张票、推荐记录和导出。
- 开奖后自动复盘。

完成标志：双色球和大乐透每期都能生成合法、不同且可复现的 5 组候选。

## Phase 5：滚动回测

- Walk-forward runner。
- 均匀随机 baseline。
- 后台任务状态和取消。
- 汇总、逐期结果和导出。
- 数据泄漏测试。

完成标志：可以比较策略与随机基线，并保存完整配置和报告。

## Phase 6：AI 集成

- AI 配置 CRUD、AES-GCM 加密和连接测试。
- OpenAI-compatible client。
- 候选重排 JSON schema。
- 推荐解释和报告摘要。
- 成本、缓存和失败状态。

完成标志：New API 或任意兼容端点可以接入，AI 异常不影响统计推荐落库。

## Phase 7：UI 完整化

- 首页首屏和响应式推荐列表。
- 亮/暗主题。
- 空状态、错误状态、加载状态和任务进度。
- 手机端适配。
- Playwright 全流程和截图检查。

完成标志：核心流程在桌面和手机 viewport 都可用，无内容重叠。

## Phase 8：发布

- 多架构镜像。
- GHCR 标签策略。
- 宝塔 Compose 文档验证。
- 数据库备份和恢复演练。
- `v1.0.0` release notes。

完成标志：全新服务器只需 `.env` 和 Compose 即可启动并完成 Setup Wizard。

## 后续扩展

满足实际需求后再评估：

- Redis + 独立 Worker。
- 多实例部署。
- 更多彩种。
- PWA。
- 本地 Ollama 容器。
- 策略插件系统。
- 通知推送。
