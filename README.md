# LottoPilot

开源的双色球 / 大乐透历史分析、候选推荐、AI 解释与滚动回测系统。

> 本系统只做历史数据分析与模型评分，**不承诺中奖**，不提供购彩交易。

## 技术栈

- 后端：Python 3.12 / FastAPI / SQLAlchemy 2 / Alembic / PostgreSQL 17
- 前端：React 19 / Vite / Tailwind CSS 4 / TanStack Query / Zustand
- CI/CD：GitHub Actions（检查 + 测试 + 镜像构建推送 GHCR）
- 部署：服务器 Docker Compose 双容器（`LottoPilot` + `LottoPilot-postgres`）

## 推荐发布路径（GitHub → Actions → 服务器）

```text
本地开发提交
  → 推送到 GitHub (main / tag v*)
  → Actions: ci.yml（结构/离线验收/后端/前端）
  → Actions: docker.yml（多架构镜像 → ghcr.io/<owner>/lottopilot）
  → 服务器 docker compose 拉取镜像并启动
```

### 1) 仓库与 Actions

1. 将本仓库推送到 GitHub（需 Packages 写入权限，默认 `GITHUB_TOKEN` 即可推 GHCR）
2. 推送 `main`/`master` 触发 CI 与 `edge` 镜像
3. 打标签 `v1.0.0` 触发正式版本与 `latest` 镜像

镜像名：

```text
ghcr.io/<owner>/lottopilot:v1.0.0
ghcr.io/<owner>/lottopilot:latest
ghcr.io/<owner>/lottopilot:edge
```

首次从 GHCR 拉取私有/容器包时，服务器可能需要：

```bash
echo $GHCR_TOKEN | docker login ghcr.io -u <github-user> --password-stdin
```

### 2) 服务器部署（Compose）

```bash
# 建议目录
cd /opt/lottopilot   # 或宝塔站点目录

# 准备配置
cp .env.example .env
# 编辑 .env：APP_SECRET_KEY / POSTGRES_PASSWORD / APP_PUBLIC_URL / COOKIE_SECURE 等
# 设置镜像：
# LOTTOPILOT_IMAGE=ghcr.io/<owner>/lottopilot:v1.0.0

# 生产推荐使用预构建镜像编排
cp deploy/baota/docker-compose.yml docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d
```

访问：

- Web：`APP_PUBLIC_URL`（默认 `http://服务器:8088`）
- Health：`/health`
- OpenAPI：`/api/docs`（生产可按需关闭）

首次打开完成 **Setup Wizard** 创建管理员，再导入/同步开奖数据。

宝塔反代、备份与升级说明：[`deploy/baota/README.md`](deploy/baota/README.md)

### 3) 源码构建启动（可选，开发机/调试）

```bash
cp .env.example .env
docker compose up -d --build
```

## 验收与文档

| 文档 | 说明 |
|---|---|
| [`docs/ACCEPTANCE_CRITERIA.md`](docs/ACCEPTANCE_CRITERIA.md) | 验收标准 |
| [`docs/ACCEPTANCE_STATUS.md`](docs/ACCEPTANCE_STATUS.md) | 当前状态 |
| [`docs/MANUAL_ACCEPTANCE_CHECKLIST.md`](docs/MANUAL_ACCEPTANCE_CHECKLIST.md) | 服务器人工清单 |
| [`docs/CI_CD_DEPLOYMENT.md`](docs/CI_CD_DEPLOYMENT.md) | CI/CD 与部署规格 |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 开发路线图 |
| [`docs/RELEASE_NOTES_v1.0.0.md`](docs/RELEASE_NOTES_v1.0.0.md) | 发布说明 |

**权威自动化证据以 GitHub Actions 为准**（offline + backend pytest + frontend build/test + docker build/push）。

## 合规声明

- AI 对最终分贡献硬顶 ≤ 10%，失败自动降级为纯统计
- 回测/推荐特征不使用未来数据（walk-forward）
- 不提供购彩下单或中奖承诺

## License

见 [`LICENSE`](LICENSE)
