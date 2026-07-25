# LottoPilot 数据库设计

## 1. 约定

- PostgreSQL 17。
- 主键统一使用 UUID v7；由应用生成，不依赖数据库扩展。
- 时间统一存 `timestamptz`，数据库和后端内部使用 UTC，前端按 Asia/Shanghai 显示。
- JSON 扩展字段使用 `jsonb`。
- 数字组合使用 `smallint[]`，并在应用层和数据库约束层双重校验。
- 所有结构变更通过 Alembic migration。

## 2. 核心表

### `users`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid | 主键 |
| `email` | varchar unique | 登录账号 |
| `password_hash` | varchar | Argon2id |
| `role` | varchar | 首版固定 `admin` |
| `is_active` | boolean | 状态 |
| `created_at` | timestamptz | 创建时间 |
| `last_login_at` | timestamptz nullable | 最近登录 |

### `user_sessions`

服务端会话表。浏览器 Cookie 只保存 256 bit 随机 token，数据库只保存 token 的 SHA-256 哈希。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid | UUID v7 主键 |
| `user_id` | uuid | 用户外键 |
| `token_hash` | char(64) unique | Cookie token 哈希 |
| `expires_at` | timestamptz | 过期时间 |
| `last_seen_at` | timestamptz | 最近使用时间 |
| `revoked_at` | timestamptz nullable | 注销/吊销时间 |
| `ip_hash` | char(64) nullable | 可选的脱敏审计信息 |
| `user_agent` | varchar nullable | 截断后的客户端信息 |
| `created_at` | timestamptz | 创建时间 |

索引：`token_hash` unique、`(user_id, expires_at desc)`。登录时轮换 token；退出和修改密码时吊销对应会话。

### `system_settings`

| 字段 | 类型 | 说明 |
|---|---|---|
| `key` | varchar primary key | 设置键 |
| `value` | jsonb | 设置值 |
| `is_secret` | boolean | 是否加密 |
| `updated_at` | timestamptz | 更新时间 |

AI Key 可放在独立表，禁止以明文出现在 `value`。

### `ai_configs`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid | 主键 |
| `name` | varchar | 配置名称 |
| `provider_type` | varchar | `openai_compatible` / `ollama` |
| `base_url` | varchar | API Base URL |
| `api_key_ciphertext` | text nullable | AES-GCM 密文 |
| `model` | varchar | 模型名 |
| `temperature` | numeric | 默认 0.2 |
| `timeout_seconds` | integer | 请求超时 |
| `is_default` | boolean | 默认配置 |
| `is_enabled` | boolean | 开关 |
| `last_test_status` | varchar nullable | 测试结果 |
| `last_tested_at` | timestamptz nullable | 测试时间 |
| `created_at` / `updated_at` | timestamptz | 时间 |

`api_key_ciphertext` 保存版本化 JSON 加密信封，包含算法版本、nonce、ciphertext 和 tag 的 Base64 值，不保存明文。

### `draws`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid | 主键 |
| `lottery_type` | varchar | `ssq` / `dlt` |
| `issue` | varchar | 官方期号 |
| `draw_date` | date | 开奖日期 |
| `primary_numbers` | smallint[] | 红球或前区 |
| `secondary_numbers` | smallint[] | 蓝球或后区 |
| `sales_amount` | numeric nullable | 销售额 |
| `pool_amount` | numeric nullable | 奖池 |
| `prize_tiers` | jsonb | 奖级信息 |
| `source_name` | varchar | 来源适配器 |
| `source_url` | text nullable | 官方详情 |
| `source_hash` | char(64) | 原始响应哈希 |
| `raw_payload` | jsonb | 原始数据 |
| `fetched_at` | timestamptz | 采集时间 |
| `created_at` / `updated_at` | timestamptz | 时间 |

约束和索引：

- unique `(lottery_type, issue)`。
- index `(lottery_type, draw_date desc)`。
- check `lottery_type in ('ssq','dlt')`。
- 数组长度和范围可通过数据库函数或触发器补充校验，应用层仍是第一校验点。

### `ingestion_runs`

记录全量同步、增量同步和文件导入。

主要字段：`id`、`job_id`、`source_name`、`lottery_type`、`mode`、`status`、`started_at`、`finished_at`、`pages_processed`、`records_seen`、`inserted_count`、`updated_count`、`skipped_count`、`error_count`、`cursor`、`error_summary`。

### `ingestion_errors`

保存失败记录：`run_id`、`source_item_key`、`raw_payload`、`error_code`、`error_message`、`created_at`。

### `jobs`

统一保存同步、推荐和回测后台任务；领域运行表保存业务结果，`jobs` 保存通用进度和取消状态。

主要字段：`id`、`job_type`、`status`、`progress_current`、`progress_total`、`resource_type`、`resource_id`、`payload_summary`、`cancel_requested_at`、`error_code`、`error_summary`、`created_by`、`created_at`、`started_at`、`finished_at`、`heartbeat_at`。

`status` 取值：`queued`、`running`、`success`、`failed`、`cancelled`。同类互斥任务使用 PostgreSQL advisory lock；任务进程退出后由启动恢复逻辑根据 heartbeat 将遗留的 `running` 任务标记为 `failed`，首版不自动重新执行 CPU 密集任务。

### `strategy_profiles`

保存推荐算法配置和版本。

主要字段：`id`、`name`、`version`、`lottery_type`、`config`、`is_default`、`is_active`、`created_at`。

配置包含窗口、特征权重、候选池大小、多样性阈值和 AI 权重上限。

### `recommendation_runs`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid | 主键 |
| `job_id` | uuid | 对应后台任务 |
| `lottery_type` | varchar | 彩种 |
| `target_issue` | varchar | 目标期号 |
| `strategy_profile_id` | uuid | 策略 |
| `data_cutoff_issue` | varchar | 使用数据截止期 |
| `data_snapshot_hash` | char(64) | 数据快照 |
| `seed` | bigint | 随机种子 |
| `candidate_count` | integer | 候选数量 |
| `ai_config_id` | uuid nullable | AI 配置 |
| `ai_status` | varchar | skipped/success/failed |
| `ai_provider` | varchar nullable | 实际供应商/适配器 |
| `ai_model` | varchar nullable | 实际模型名 |
| `ai_prompt_version` | varchar nullable | 提示词版本 |
| `ai_response_hash` | char(64) nullable | 原始响应哈希 |
| `ai_metrics` | jsonb | 耗时、token 和错误分类，不含密钥 |
| `status` | varchar | queued/running/success/failed |
| `metrics` | jsonb | 运行指标 |
| `created_at` / `finished_at` | timestamptz | 时间 |

`job_id` 是 unique 外键。运行状态还允许 `cancelled`，并与对应 `jobs.status` 同事务更新。

### `recommendation_tickets`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid | 主键 |
| `run_id` | uuid | 推荐运行 |
| `rank` | smallint | 1–5 |
| `primary_numbers` | smallint[] | 主区号码 |
| `secondary_numbers` | smallint[] | 次区号码 |
| `statistical_score` | numeric | 统计分 |
| `ai_score` | numeric nullable | AI 归一化分 |
| `final_score` | numeric | 最终分 |
| `feature_summary` | jsonb | 特征摘要 |
| `tags` | jsonb | 展示标签 |
| `explanation` | text nullable | AI 解释 |
| `created_at` | timestamptz | 时间 |

unique `(run_id, rank)`。

### `recommendation_results`

开奖后复盘：`ticket_id`、`draw_id`、`primary_hits`、`secondary_hits`、`prize_level`、`prize_rule_set_id`、`evaluated_at`。

### `prize_rule_sets`

保存按彩种版本化的奖级判断规则：`id`、`lottery_type`、`version`、`effective_from_issue`、`effective_to_issue`、`rules`、`created_at`。已被复盘结果引用的规则版本不可修改。

### `backtest_runs`

记录回测配置、状态和汇总：`job_id`、`lottery_type`、`strategy_profile_id`、`start_issue`、`end_issue`、`seed`、`baseline_trials`、`status`、`summary`、`started_at`、`finished_at`。`job_id` 是 unique 外键，状态允许 `cancelled`。

### `backtest_issue_results`

逐期结果：`backtest_run_id`、`target_draw_id`、`training_cutoff_draw_id`、`tickets`、`hit_metrics`、`baseline_metrics`、`runtime_ms`。

### `audit_logs`

记录设置修改、数据导入、AI Key 更新、策略变更和手动生成行为。保存 `actor_id`、`action`、`resource_type`、`resource_id`、`metadata`、`request_id`、`created_at`，metadata 中不得保存密钥明文。

## 3. 迁移规则

1. migration 必须支持从上一发布版本向前升级。
2. 破坏性字段删除分两次发布：先停止使用，再删除。
3. 大表新增非空字段时先 nullable、回填、再加约束。
4. CI 在空数据库执行全量 upgrade，并从上一标签数据库执行升级测试。
5. 应用启动前运行 `alembic upgrade head`，失败则容器退出并保留日志。
