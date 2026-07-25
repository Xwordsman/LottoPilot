# LottoPilot v1.0.0 Release Notes

发布日期：2026-07-24  
产品名：`LottoPilot`  
镜像：`ghcr.io/<owner>/lottopilot:v1.0.0` / `lottopilot:latest`

## 范围

本版本交付统计优先的自托管彩票分析系统（双色球 / 大乐透）：

- 初始化向导与 Cookie 会话认证
- 官方源同步与 CSV 导入
- 频率 / 遗漏 / 热冷 / 共现统计
- 可复现 5 组推荐（固定 seed + 快照哈希）
- Walk-forward 回测与随机基线
- AI 配置加密、连通性测试与推荐有限重排（权重 ≤ 10%，失败降级）
- 开奖后推荐复盘（命中 / 奖级）与 JSON/CSV 导出
- Docker Compose 一键部署与宝塔部署说明

## 安全与合规声明

- 仅做历史数据分析与模型评分，**不承诺中奖**
- 不提供购彩交易 / 下单能力
- AI 对最终分贡献硬顶 10%
- 回测与推荐特征不使用未来数据

## 升级 / 安装

### 全新服务器（推荐）

1. 复制 `.env.example` 为 `.env` 并修改密钥与数据库密码  
2. `docker compose up -d --build`  
3. 打开 `APP_PUBLIC_URL` 完成 Setup Wizard  
4. 同步或导入历史开奖 ≥ 20 期  
5. 生成推荐并（可选）配置 AI

### 备份与恢复

见：

- `scripts/backup_pg.sh`
- `scripts/restore_pg.sh`
- `deploy/baota/README.md`

## 已知限制

- 首版不内置 Redis / 独立 Worker
- 官方源同步依赖外网可达性；不可达时使用 CSV 导入
- Playwright 全流程 E2E 仍为后续增强
- 本机/CI 未通过时，不得将运行时门禁标为已完成

## 验收依据

- `docs/ACCEPTANCE_CRITERIA.md`
- `docs/ACCEPTANCE_STATUS.md`
- `scripts/offline_acceptance.py`
- `scripts/check_structure.py`
- `scripts/local_api_smoke.py`
- `scripts/local_sqlite_e2e.py`
- `scripts/local_fullstack_smoke.py`
