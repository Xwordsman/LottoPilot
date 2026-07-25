# LottoPilot 人工验收清单

与 `docs/ACCEPTANCE_CRITERIA.md` 第 9.2 节对齐。  
**推荐路径：GitHub Actions 构建镜像 → 服务器 Docker Compose 部署后勾选。**

## 服务器 Docker 部署路径

- [ ] GitHub Actions `ci.yml` 全绿
- [ ] GitHub Actions `docker.yml` 已推送 `ghcr.io/<owner>/lottopilot:<tag>`
- [ ] 服务器已 `docker login ghcr.io`（如包为 private）
- [ ] `.env` 已从 `.env.example` 生成并修改密钥/密码/`APP_PUBLIC_URL`
- [ ] `LOTTOPILOT_IMAGE` 指向正确版本标签
- [ ] `docker compose -f deploy/baota/docker-compose.yml up -d` 成功
- [ ] `GET /health` 返回 success 信封
- [ ] `GET /api/v1/system/ready` database/migrations = ok


## 环境（兼容旧清单）
## 认证

- [ ] 首次访问进入 Setup Wizard
- [ ] 创建管理员后自动登录
- [ ] 刷新页面仍保持登录
- [ ] 退出后访问受保护页跳转登录
- [ ] 设置页可见最近审计日志（setup/login 等动作）

## 数据

- [ ] 官方同步 SSQ 或 DLT 成功，或
- [ ] 使用 `backend/tests/fixtures/ssq_import_20.csv` 导入 20 期
- [ ] 开奖列表可查询最新期
- [ ] 开奖页 CSV 预览与提交导入
- [ ] `GET /lotteries` 返回双彩种规则

## 统计 / 推荐 / 回测

- [ ] 统计页显示频率与遗漏
- [ ] 推荐生成 5 组合法号码，含免责声明
- [ ] 固定 seed 时结果可复现（可对比两次 snapshot/seed）
- [ ] 推荐页可输入 seed / 目标期并在结果展示
- [ ] 总览页可选 seed 生成
- [ ] 回测 running/queued 时可取消
- [ ] 回测区间可出 summary 与相对基线
- [ ] 回测页可见逐期结果表
- [ ] 目标期开奖入库后可复盘命中
- [ ] 推荐页可“重生成解释”
- [ ] 推荐导出 JSON / CSV 可用
- [ ] 回测导出 JSON / CSV 可用
- [ ] 总览页展示最近推荐（若已有记录）

## 策略

- [ ] `/strategies` 可列出默认策略
- [ ] 可创建实验版本（名称/版本/候选池）
- [ ] 可启用策略
- [ ] 可设为默认（填写回测摘要 JSON）

## AI / 系统设置

- [ ] 设置页保存 AI 配置
- [ ] 列表仅显示脱敏 Key
- [ ] 连通性测试返回 latency/status
- [ ] 可设为默认 AI 配置
- [ ] 可删除 AI 配置（被引用时软删）
- [ ] 关闭 AI 或 AI 失败时推荐仍可生成
- [ ] 系统设置可保存时区/调度/候选池
- [ ] AI 权重上限 >0.10 时被拒绝

## 运维

- [ ] `./scripts/backup_pg.sh ./backups` 生成 gzip SQL
- [ ] （可选）restore 演练成功
- [ ] 宝塔/反代 HTTPS 可访问

- [ ] 顶栏可切换亮/暗主题，刷新后保持
- [ ] 列表失败可见 ErrorState 并可重试（推荐/回测/任务/统计/设置/策略）

## 离线门禁（开发机最低）

- [ ] `python scripts/check_structure.py` → STRUCTURE_ACCEPTANCE_OK
- [ ] `python scripts/offline_acceptance.py` → OFFLINE_ACCEPTANCE_OK
- [ ] `python scripts/run_unit_offline.py` → UNIT_OFFLINE_OK

## API 自动化对应（无 Docker）

下列项可由 `python scripts/local_sqlite_e2e.py` → `LOCAL_SQLITE_E2E_OK` 作为 API 层证据（**不替代 UI 勾选**）：

- [x] Setup / 登录 Cookie / 登出 / 再登录
- [x] CSV 导入 20 期 + 列表/最新期
- [x] 统计 overview 频率与遗漏
- [x] 推荐 5 注 + seed 可复现 + 复盘 + 导出 JSON/CSV
- [x] 回测 summary + 逐期 + 导出
- [x] 策略创建/启用/设默认
- [x] AI 配置脱敏保存/默认/删除；连通性端点可调用
- [x] 系统设置读写；`ai_weight_cap>0.10` 拒绝
- [x] 审计日志非空；jobs 列表
- [x] `/system/ready` database=ok（migrations 可为 pending）

仍需人工/Compose：

- [ ] Docker Compose 启动与 `.env`
- [ ] 前端 Setup Wizard / 主题 / ErrorState 视觉
- [ ] 宝塔反代与备份脚本实机演练
