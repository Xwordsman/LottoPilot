# LottoPilot 测试与质量规格

## 1. 目标

测试重点按风险排序：开奖数据正确性、号码合法性、回测无泄漏、推荐可复现、密钥安全、部署可启动、前端关键流程可用。

## 2. 后端测试

### 单元测试

覆盖：

- 双色球和大乐透号码校验。
- 官方 JSON parser。
- 日期、金额和期号解析。
- 频率、遗漏、和值、跨度、分区等特征。
- seed 生成。
- 候选去重和多样性选择。
- MMR 相似度。
- 评分归一化。
- AI 结构化输出校验。
- API Key 加密、掩码和清除语义。

### 属性测试

使用 Hypothesis 生成大量输入，验证：

- 任意输出都满足彩种号码范围、数量、唯一性和排序。
- 同 seed 和同输入输出一致。
- 最终始终返回 5 组互不相同的组合。
- score 始终有限且在约定范围。
- 未来数据不会进入目标期特征。

### Repository/数据库测试

- 在临时 PostgreSQL 中执行 migration。
- 测试 `(lottery_type, issue)` 幂等 upsert。
- 测试推荐运行、5 张票和复盘事务完整性。
- 测试分页、筛选和索引查询。
- 测试并发同步任务锁。

### API 集成测试

使用 FastAPI TestClient/HTTPX ASGI transport：

- Setup 只能成功一次。
- 登录、退出、Cookie、Origin 校验。
- 同步任务创建和冲突。
- 推荐创建、查询、导出。
- AI 配置 API 不返回 Key 明文。
- 统一错误 envelope 和 request ID。

## 3. 数据采集测试

- 真实官方响应保存为测试 fixture，去除无关大字段。
- parser 测试使用 fixture，不依赖实时网络。
- 测试官方字段顺序变化、字段缺失、空值和新增字段。
- 测试 WAF HTML 被识别为源错误，而不是 JSON 解析崩溃。
- 测试 429/5xx 的退避和重试上限。
- 实时官方 smoke test 只在手工 workflow 中低频执行。

## 4. 推荐和回测测试

### 固定黄金样本

保存一小份固定历史数据和策略配置，断言：

- 快照哈希稳定。
- 特征值在允许误差内稳定。
- 同 seed 的 5 组结果稳定。

若算法有意变化，更新黄金样本时必须附回测报告和变更说明。

### 无泄漏测试

对目标期 `t`：

1. 生成推荐结果 A。
2. 修改目标期和未来期号码。
3. 再生成结果 B。
4. A 与 B 必须一致。

### 随机基线测试

- 基线采样必须均匀。
- 基线使用独立派生 seed。
- 报告包含 trial 数和分布，不只包含平均值。

## 5. AI 测试

Fake provider 场景：

- 正常 JSON。
- Markdown 包裹 JSON。
- 非 JSON 文本。
- 未知 candidate ID。
- 重复 candidate ID。
- score 越界。
- 响应超时。
- 429 和 5xx。

所有异常场景都应回到统计排序并记录状态。

## 6. 前端测试

### 组件测试

- NumberBall 对两种彩票的颜色和两位数格式。
- 推荐卡片显示 5 组和状态。
- SecretInput 不暴露原 Key。
- DataTable 分页和过滤。
- AI 测试连接状态。
- JobProgress 完成、失败和取消状态。

### 页面集成测试

- 登录到首页。
- 彩种切换刷新对应数据。
- 生成推荐并轮询任务。
- 查看推荐详情。
- 导入预览和提交。
- 修改 AI 配置并测试连接。

### Playwright E2E

最低关键流程：

1. Setup -> 登录 -> 首页。
2. 同步 fixture 数据 -> 生成双色球 5 组。
3. 切换大乐透 -> 生成 5 组。
4. 配置 fake AI -> 生成解释。
5. 创建短区间回测 -> 查看结果。

桌面端和移动端各跑一个 viewport，并做无重叠截图检查。

## 7. 性能测试

首版基线目标：

- 50,000 候选普通 CPU 下在可接受时间内完成，目标小于 10 秒，最终以 CI 基准机记录为准。
- 普通列表 API P95 小于 300ms，不含外部 AI 和官方源。
- 首页首屏 API 避免 N+1 查询。
- 大回测作为后台任务，不阻塞健康检查和普通查询。

## 8. CI 质量门禁

每个 PR 必须通过：

```text
backend format
backend lint
backend typecheck
backend unit + integration tests
frontend format/lint
frontend typecheck
frontend unit tests
frontend production build
Docker image build
container smoke test
```

建议命令：

```bash
# backend
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy lottopilot
uv run pytest

# frontend
npm ci
npm run lint
npm run typecheck
npm run test -- --run
npm run build
```

## 9. 完成定义

一个功能只有同时满足以下条件才算完成：

- 实现通过类型检查和 lint。
- 正常流程和关键异常都有测试。
- API 和 UI 状态完整。
- migration 可在空库和已有库运行。
- 相关文档更新。
- Docker smoke test 通过。

## Offline acceptance (no third-party)

```bash
python scripts/check_structure.py
python scripts/offline_acceptance.py
python scripts/run_unit_offline.py
```
