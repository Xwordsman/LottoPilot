# LottoPilot

开源的双色球 / 大乐透历史分析、候选推荐、AI 解释与滚动回测系统。

> **合规声明**：本项目只做历史数据分析与模型评分，**不承诺中奖**，不提供购彩、代投、充值或支付能力。请理性对待推荐结果。

[![CI](https://github.com/Xwordsman/LottoPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Xwordsman/LottoPilot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Image-ghcr.io%2Fxwordsman%2Flottopilot-blue.svg)](https://github.com/Xwordsman/LottoPilot/pkgs/container/lottopilot)

---

## 功能特性

- **双彩种支持**：双色球（SSQ）与大乐透（DLT）
- **历史数据同步**：官方源全量 / 增量同步，支持 CSV / XLSX 导入
- **统计分析**：频率、遗漏、和值、跨度、奇偶、分区、连号、趋势等
- **本期 5 组候选**：统计评分 + 去重 + 多样性筛选
- **AI 可选增强**：AI 权重硬顶 ≤ 10%，失败自动降级为纯统计
- **滚动回测**：walk-forward，不用未来数据
- **推荐复盘**：开奖后自动计算命中情况
- **初始化向导**：首次启动创建管理员、可选配置 AI、触发同步
- **一键部署**：Docker 双容器（`LottoPilot` + `LottoPilot-postgres`）

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 17 |
| 前端 | React 19 · Vite · Tailwind CSS 4 · TanStack Query · Zustand |
| 认证 | Cookie Session · Argon2id |
| CI/CD | GitHub Actions · 多架构镜像 · GHCR |
| 部署 | Docker Compose（宝塔可直接粘贴编排） |

---

## 快速部署（推荐，和 new-api 一样简单）

镜像地址：

```text
ghcr.io/xwordsman/lottopilot:latest
```

> `main` 分支推送成功后会自动更新 `latest`；打 `v*` 版本标签时也会更新 `latest`。

### 方式 A：宝塔「容器编排」

1. 打开 **Docker → 容器编排 → 添加**
2. **编排名称**：`LottoPilot`
3. **来源**：编辑
4. **compose 内容**：粘贴下面整段
5. **.env 内容**：留空
6. 点确定并启动

```yaml
services:
  postgres:
    image: postgres:17-alpine
    container_name: LottoPilot-postgres
    restart: always
    environment:
      POSTGRES_USER: lottopilot
      POSTGRES_PASSWORD: change-me-db-password
      POSTGRES_DB: lottopilot
      TZ: Asia/Shanghai
    volumes:
      - lottopilot_pgdata:/var/lib/postgresql/data
    networks:
      - lottopilot

  app:
    image: ghcr.io/xwordsman/lottopilot:latest
    container_name: LottoPilot
    restart: always
    depends_on:
      - postgres
    ports:
      - "8088:8000"
    environment:
      APP_ENV: production
      APP_DEBUG: "false"
      APP_PUBLIC_URL: http://127.0.0.1:8088
      APP_SECRET_KEY: change-me-to-a-long-random-string
      COOKIE_SECURE: "false"
      POSTGRES_HOST: postgres
      POSTGRES_PORT: "5432"
      POSTGRES_DB: lottopilot
      POSTGRES_USER: lottopilot
      POSTGRES_PASSWORD: change-me-db-password
      DATABASE_URL: postgresql+psycopg://lottopilot:change-me-db-password@postgres:5432/lottopilot
      TZ: Asia/Shanghai
      SYNC_ENABLED: "true"
      DRAW_DATA_SOURCE: auto
    networks:
      - lottopilot

networks:
  lottopilot:
    driver: bridge

volumes:
  lottopilot_pgdata:
```

启动前至少改这 3 处（两处密码保持一致）：

1. `POSTGRES_PASSWORD` / `DATABASE_URL` 中的数据库密码
2. `APP_SECRET_KEY` 改成长随机串
3. `APP_PUBLIC_URL` 改成实际访问地址
   - 直连：`http://公网IP:8088`
   - 域名 + HTTPS 反代：`https://你的域名`，并把 `COOKIE_SECURE` 改为 `"true"`

### 方式 B：命令行 Compose

```bash
# 若 GHCR 包为 Private，先登录（Public 可跳过）
echo "$GHCR_TOKEN" | docker login ghcr.io -u xwordsman --password-stdin

mkdir -p /opt/lottopilot && cd /opt/lottopilot
# 使用仓库中的精简编排：deploy/baota/docker-compose.yml

# 编辑 compose 中的密码 / SECRET / PUBLIC_URL 后：
docker compose -f docker-compose.yml up -d
docker compose ps
```

### 访问与健康检查

| 地址 | 说明 |
|---|---|
| `http://服务器:8088/` | Web 首页 / Setup 向导 |
| `http://服务器:8088/health` | 进程健康 |
| `http://服务器:8088/api/v1/system/ready` | 数据库与迁移就绪 |
| `http://服务器:8088/api/docs` | OpenAPI（生产可按需关闭） |

首次打开站点 → **Setup Wizard** 创建管理员 → 同步开奖数据 → 开始使用。

宝塔反向代理目标：`http://127.0.0.1:8088`

---

## 本地开发（可选）

### 源码构建启动

```bash
git clone https://github.com/Xwordsman/LottoPilot.git
cd LottoPilot
cp .env.example .env
# 按需修改 .env
docker compose up -d --build
```

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
ruff check app tests
mypy app
pytest -q
```

### 前端

```bash
cd frontend
npm ci
npm run dev
npm test
npm run build
```

---

## 发布与镜像

```text
本地提交
  → push main / tag v*
  → GitHub Actions CI
      · Offline checks
      · Backend (ruff / mypy / pytest)
      · Frontend (build / test)
      · Docker multi-arch → GHCR
  → 服务器 docker compose pull && up -d
```

| 触发 | 镜像标签 |
|---|---|
| 推送到 `main` | `latest`、`edge`、`main`、`sha-xxxx` |
| 打标签 `v1.0.0` | `latest`、`1.0.0`、`1.0` 等 |

镜像：

```text
ghcr.io/xwordsman/lottopilot:latest
```

---

## 目录结构

```text
LottoPilot/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 路由
│   │   ├── core/            # 配置、常量、安全
│   │   ├── db/              # 会话与类型
│   │   ├── models/          # ORM
│   │   ├── services/        # 业务（同步/统计/推荐/回测/AI）
│   │   └── utils/
│   ├── alembic/             # 数据库迁移
│   └── tests/
├── frontend/                # React 前端
│   └── src/
│       ├── app/
│       ├── components/
│       └── features/
├── deploy/
│   ├── SERVER_QUICKSTART.md # 服务器速查
│   └── baota/
│       ├── docker-compose.yml  # 生产精简编排（无需单独 .env）
│       └── README.md
├── docs/                    # 产品 / 架构 / API / 验收文档
├── scripts/                 # 入口、离线验收、备份恢复
├── docker-compose.yml       # 本地源码构建编排
├── Dockerfile
└── .github/workflows/ci.yml # 单一 CI 工作流
```

---

## 页面一览

| 路由 | 页面 |
|---|---|
| `/setup` | 初始化向导 |
| `/login` | 登录 |
| `/` | 推荐首页（5 组候选） |
| `/history` | 历史开奖 |
| `/analysis` | 统计分析 |
| `/backtests` | 历史回测 |
| `/recommendations` | 推荐记录 / 复盘 |
| `/data` | 数据管理（同步 / 导入） |
| `/settings/ai` | AI 设置 |
| `/settings/system` | 系统设置 |

---

## 核心配置说明

生产环境推荐直接写在 compose 的 `environment` 中（与 new-api 相同思路）：

| 变量 | 说明 | 示例 |
|---|---|---|
| `APP_PUBLIC_URL` | 对外访问根地址 | `https://lotto.example.com` |
| `APP_SECRET_KEY` | 会话签名密钥 | 长随机串 |
| `COOKIE_SECURE` | HTTPS 时设 `true` | `true` / `false` |
| `POSTGRES_PASSWORD` | 数据库密码 | 强密码 |
| `DATABASE_URL` | SQLAlchemy 连接串 | 与上面密码一致 |
| `SYNC_ENABLED` | 是否启用定时同步 | `true` |
| `DRAW_DATA_SOURCE` | 开奖数据源：`auto`（500彩票网优先，失败回退官方）/`500com`/`official` | `auto` |
| `AI_WEIGHT_CAP` | AI 权重上限（≤0.10） | `0.10` |

完整示例见 [`.env.example`](.env.example)（本地开发用）。

---

## 设计约束（硬性）

1. **不承诺中奖**，不做购彩交易
2. **AI 权重 ≤ 10%**，失败 fail-open 回退纯统计
3. 推荐 / 回测特征 **禁止使用未来数据**（walk-forward）
4. AI 输出号码必须经后端规则校验后才能入库展示
5. 发布权威证据以 **GitHub Actions + 服务器 Compose** 为准

---

## 文档

| 文档 | 说明 |
|---|---|
| [`docs/PRODUCT.md`](docs/PRODUCT.md) | 产品规格 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 架构设计 |
| [`docs/API.md`](docs/API.md) | HTTP API |
| [`docs/DATABASE.md`](docs/DATABASE.md) | 数据库 |
| [`docs/RECOMMENDATION_ENGINE.md`](docs/RECOMMENDATION_ENGINE.md) | 推荐引擎 |
| [`docs/AI_INTEGRATION.md`](docs/AI_INTEGRATION.md) | AI 集成 |
| [`docs/CI_CD_DEPLOYMENT.md`](docs/CI_CD_DEPLOYMENT.md) | CI/CD 与部署 |
| [`docs/ACCEPTANCE_CRITERIA.md`](docs/ACCEPTANCE_CRITERIA.md) | 验收标准 |
| [`docs/MANUAL_ACCEPTANCE_CHECKLIST.md`](docs/MANUAL_ACCEPTANCE_CHECKLIST.md) | 人工验收清单 |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 开发路线图 |
| [`deploy/SERVER_QUICKSTART.md`](deploy/SERVER_QUICKSTART.md) | 服务器速查 |
| [`deploy/baota/README.md`](deploy/baota/README.md) | 宝塔部署说明 |

---

## 升级

```bash
# 拉取最新 latest 镜像
docker compose pull
docker compose up -d
# entrypoint 会自动 alembic upgrade head
```

建议升级前备份：

```bash
./scripts/backup_pg.sh ./backups
```

---

## 常见问题

**Q: 为什么不是 Docker Hub，而是 GHCR？**  
A: CI 直接推送到 `ghcr.io/xwordsman/lottopilot`，与 GitHub 仓库一体。

**Q: 拉镜像 401？**  
A: Package 为 Private 时需要：

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u xwordsman --password-stdin
```

Token 需具备 `read:packages`。也可把 Package 设为 Public。

**Q: 为什么宝塔不用单独填 .env？**  
A: 生产精简编排已把配置写在 compose 的 `environment` 中，和 new-api 一样，粘贴即可启动。

**Q: AI 不配能不能用？**  
A: 可以。统计引擎独立运行；AI 只是可选增强，失败自动降级。

---

## 贡献

欢迎 Issue / PR。提交前建议：

```bash
# 后端
cd backend && ruff check app tests && mypy app && pytest -q

# 前端
cd frontend && npm test && npm run build

# 仓库结构与离线验收
python scripts/check_structure.py
python scripts/offline_acceptance.py
```

---

## License

[MIT](LICENSE) © 2026 LottoPilot Contributors
