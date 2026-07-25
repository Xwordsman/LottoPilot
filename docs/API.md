# LottoPilot HTTP API 规格

## 1. 基础约定

- 业务 Base path：`/api/v1`；只有进程健康检查使用根路径 `/health`。
- JSON：UTF-8，字段使用 snake_case。
- 时间：ISO 8601，带时区。
- 分页：`page` 从 1 开始，`page_size` 默认 20，最大 100。
- 请求 ID：接收或生成 `X-Request-ID`，响应头回传。

成功响应：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "req_..."
}
```

失败响应：

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "DRAW_VALIDATION_FAILED",
    "message": "开奖号码校验失败",
    "details": {}
  },
  "request_id": "req_..."
}
```

列表响应的 `data`：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "total_pages": 0
}
```

## 2. 认证

首版采用管理员邮箱和密码登录。服务端生成 256 bit 随机 session token，Cookie 保存原 token，数据库 `user_sessions` 只保存 SHA-256 哈希。Cookie 设置 Secure、HttpOnly、SameSite=Lax 和明确过期时间，前端 JavaScript 不读取 token。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/setup/status` | 是否已初始化 |
| POST | `/setup` | 创建管理员和默认设置，只能执行一次 |
| POST | `/auth/login` | 登录 |
| POST | `/auth/logout` | 退出 |
| GET | `/auth/me` | 当前用户 |

所有非 GET/HEAD 请求校验 `Origin` 是否与站点同源；生产环境拒绝缺失或不匹配的 Origin。登录成功轮换 token，退出时吊销会话。公开部署必须通过 HTTPS。

## 3. 健康与系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 绝对路径 `/health`，只检查进程，不使用 `/api/v1` 前缀 |
| GET | `/system/ready` | 数据库和 migration readiness |
| GET | `/system/info` | 版本、commit、构建时间、数据最新期 |
| GET | `/system/jobs` | 最近后台任务 |
| GET | `/system/jobs/{id}` | 任务状态 |

## 4. 彩种与开奖

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/lotteries` | 返回 ssq/dlt 规则和状态 |
| GET | `/draws` | 按彩种、期号、日期分页查询 |
| GET | `/draws/latest` | 最新开奖 |
| GET | `/draws/{lottery_type}/{issue}` | 单期开奖详情 |
| POST | `/draws/sync` | 创建增量或全量同步任务 |
| GET | `/draws/sync-runs` | 同步记录 |
| POST | `/draws/import/preview` | 上传并预览 CSV/XLSX |
| POST | `/draws/import/commit` | 确认导入 |

`POST /draws/sync`：

```json
{
  "lottery_type": "ssq",
  "mode": "incremental"
}
```

返回 `202 Accepted` 和 job ID。

## 5. 统计分析

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/analytics/overview` | 统计摘要 |
| GET | `/analytics/numbers` | 号码频率、遗漏、趋势 |
| GET | `/analytics/distributions` | 和值、跨度、奇偶、分区等分布 |
| GET | `/analytics/cooccurrence` | 受限的共现统计 |

通用查询：

```text
lottery_type=ssq
window=60
end_issue=2026083
```

## 6. 推荐

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/recommendations` | 生成推荐 |
| GET | `/recommendations` | 推荐运行列表 |
| GET | `/recommendations/{run_id}` | 推荐详情和 5 组组合 |
| POST | `/recommendations/{run_id}/explanations` | 只重生成 AI 解释 |
| POST | `/recommendations/{run_id}/evaluate` | 手动触发复盘，通常自动执行 |
| GET | `/recommendations/{run_id}/export` | CSV/JSON 导出 |

创建请求：

```json
{
  "lottery_type": "ssq",
  "target_issue": null,
  "strategy_profile_id": null,
  "seed": null,
  "use_ai": true
}
```

统一采用 job 模式，返回 `202 Accepted`：

```json
{
  "job_id": "...",
  "recommendation_run_id": "...",
  "status": "queued"
}
```

推荐详情必须返回：数据截止期、快照哈希、策略版本、seed、AI 状态、5 张 ticket 和复盘结果。

## 7. 回测

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/backtests` | 创建回测任务 |
| GET | `/backtests` | 回测列表 |
| GET | `/backtests/{id}` | 状态和汇总 |
| GET | `/backtests/{id}/issues` | 逐期结果 |
| GET | `/backtests/{id}/export` | 导出报告 |
| POST | `/backtests/{id}/cancel` | 请求取消 |

创建请求：

```json
{
  "lottery_type": "dlt",
  "strategy_profile_id": "...",
  "start_issue": "24001",
  "end_issue": "25001",
  "seed": 42,
  "baseline_trials": 100
}
```

## 8. 策略配置

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/strategies` | 策略列表 |
| GET | `/strategies/{id}` | 配置详情 |
| POST | `/strategies` | 从现有配置复制创建新版本 |
| PATCH | `/strategies/{id}` | 只允许修改未冻结实验版本 |
| POST | `/strategies/{id}/activate` | 启用 |
| POST | `/strategies/{id}/set-default` | 设为默认，需回测摘要 |

已经被推荐运行引用的策略版本视为不可变。

## 9. AI 设置

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/settings/ai` | 列表，Key 仅返回掩码 |
| POST | `/settings/ai` | 新建配置 |
| PATCH | `/settings/ai/{id}` | 更新配置 |
| DELETE | `/settings/ai/{id}` | 删除非引用配置或软删除 |
| POST | `/settings/ai/{id}/test` | 测试连接 |
| POST | `/settings/ai/{id}/set-default` | 设为默认 |

## 10. 系统设置

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/settings/system` | 获取非敏感设置 |
| PATCH | `/settings/system` | 修改时区、调度、候选池上限等 |
| GET | `/audit-logs` | 审计日志分页 |

## 11. 错误码

| 错误码 | HTTP | 含义 |
|---|---:|---|
| `AUTH_REQUIRED` | 401 | 需要登录 |
| `FORBIDDEN` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `VALIDATION_ERROR` | 422 | 请求参数错误 |
| `DRAW_VALIDATION_FAILED` | 422 | 开奖数据不合法 |
| `SOURCE_RATE_LIMITED` | 503 | 官方源限流或 WAF |
| `AI_CONNECTION_FAILED` | 502 | AI 连接失败 |
| `AI_OUTPUT_INVALID` | 502 | AI 输出结构错误 |
| `JOB_CONFLICT` | 409 | 同类任务正在执行 |
| `STRATEGY_IMMUTABLE` | 409 | 策略版本已经冻结 |
| `INTERNAL_ERROR` | 500 | 未分类错误 |

## 12. OpenAPI

- FastAPI 自动生成 `/docs` 和 `/openapi.json`，生产环境可通过设置关闭公开 Swagger。
- API 变更先更新本文档和 Pydantic schema，再修改实现。
- 前端类型优先从 OpenAPI 生成，减少手写类型漂移。
