# LottoPilot CI/CD 与部署规格

## 1. 发布目标

GitHub Actions 自动完成：

```text
代码检查 -> 测试 -> 前端构建 -> Docker 多架构构建
         -> 推送 GHCR -> 生成版本元数据
```

服务器部署由宝塔 Docker Compose 拉取镜像并重建。自动构建和生产上线分开控制。

## 2. 镜像命名

产品和仓库名为 `LottoPilot`。OCI 镜像仓库名要求小写，因此镜像使用：

```text
ghcr.io/OWNER/lottopilot:latest
ghcr.io/OWNER/lottopilot:v1.0.0
ghcr.io/OWNER/lottopilot:sha-COMMIT
```

产品展示名和仓库展示名统一使用 `LottoPilot`；镜像仓库使用规范化的小写 `lottopilot`。

## 3. Git 分支和标签

- Pull Request：只测试和构建，不推正式镜像。
- `main`：推送 `edge` 和 `sha-*`。
- `v*` tag：推送版本标签和 `latest`。
- 生产 Compose 推荐固定版本，例如 `v1.0.0`；确认升级时修改标签或拉取新版本。

## 4. GitHub Actions 工作流

建议工作流：

```text
.github/workflows/ci.yml
.github/workflows/docker.yml
.github/workflows/manual-source-smoke.yml
```

`ci.yml`：

1. Backend：安装 Python 和 uv，执行 `uv sync --frozen`，再运行 ruff、mypy、pytest。
2. Frontend：安装 Node、`npm ci`、lint、typecheck、test、build。
3. Integration：启动 PostgreSQL service container，执行 migrations 和集成测试。

`docker.yml`：

1. `docker/setup-qemu-action`。
2. `docker/setup-buildx-action`。
3. `docker/login-action` 登录 GHCR，使用 `GITHUB_TOKEN`。
4. `docker/metadata-action` 生成 tag 和 OCI label。
5. `docker/build-push-action` 构建 `linux/amd64,linux/arm64`。
6. 启动镜像，等待 `/health`，执行 smoke test。
7. tag 发布时推送 GHCR。

Workflow 需要：

```yaml
permissions:
  contents: read
  packages: write
```

## 5. Dockerfile 结构

多阶段构建：

```text
Stage 1: node builder
  npm ci
  npm run test -- --run
  npm run build

Stage 2: python dependency builder
  uv sync --frozen --no-dev

Stage 3: python slim runtime
  copy backend
  copy frontend/dist -> lottopilot/static
  create non-root user
  expose 8000
  healthcheck
  entrypoint -> migration -> uvicorn
```

运行镜像中不保留 Node、编译器和测试依赖。

## 6. 环境变量

`deploy/.env.example` 至少包含：

```env
TZ=Asia/Shanghai
APP_ENV=production
APP_SECRET=REPLACE_WITH_32_BYTE_RANDOM_SECRET
POSTGRES_DB=lottopilot
POSTGRES_USER=lottopilot
POSTGRES_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
SCHEDULER_ENABLED=true
LOG_LEVEL=INFO
SESSION_COOKIE_SECURE=true
```

AI Key 推荐在后台加密配置，也可使用：

```env
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

## 7. Docker Compose

```yaml
services:
  lottopilot:
    image: ghcr.io/OWNER/lottopilot:v1.0.0
    container_name: LottoPilot
    restart: unless-stopped
    ports:
      - "127.0.0.1:8088:8000"
    environment:
      TZ: ${TZ:-Asia/Shanghai}
      APP_ENV: ${APP_ENV:-production}
      APP_SECRET: ${APP_SECRET:?APP_SECRET is required}
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-lottopilot}:${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}@lottopilot-postgres:5432/${POSTGRES_DB:-lottopilot}
      SCHEDULER_ENABLED: ${SCHEDULER_ENABLED:-true}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      SESSION_COOKIE_SECURE: ${SESSION_COOKIE_SECURE:-true}
      LLM_BASE_URL: ${LLM_BASE_URL:-}
      LLM_API_KEY: ${LLM_API_KEY:-}
      LLM_MODEL: ${LLM_MODEL:-}
    volumes:
      - lottopilot_data:/app/data
    depends_on:
      lottopilot-postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    networks:
      - lottopilot-network

  lottopilot-postgres:
    image: postgres:17-alpine
    container_name: LottoPilot-postgres
    restart: unless-stopped
    environment:
      TZ: ${TZ:-Asia/Shanghai}
      POSTGRES_DB: ${POSTGRES_DB:-lottopilot}
      POSTGRES_USER: ${POSTGRES_USER:-lottopilot}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
    volumes:
      - lottopilot_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-lottopilot} -d ${POSTGRES_DB:-lottopilot}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - lottopilot-network

volumes:
  lottopilot_data:
  lottopilot_postgres_data:

networks:
  lottopilot-network:
    driver: bridge
```

首版没有 Redis。若后续加入独立队列，命名为 `LottoPilot-worker` 和 `LottoPilot-redis`。

## 8. 宝塔部署

1. GitHub 仓库 Actions 构建并推送 GHCR。
2. GHCR package 设置为 public；私有包则在服务器执行 `docker login ghcr.io -u OWNER -p TOKEN`。
3. 宝塔面板进入 Docker -> 容器编排。
4. 新建 LottoPilot 编排，填入 Compose。
5. 在编排目录创建 `.env`，填写 APP_SECRET 和 PostgreSQL 密码。
6. 启动编排。
7. 宝塔网站添加反向代理到 `http://127.0.0.1:8088`。
8. 配置域名证书和 HTTPS。
9. 打开域名完成 Setup Wizard。

可使用 `openssl rand -base64 48` 生成 `APP_SECRET`。`.env` 权限应限制为仅部署用户可读，且不提交到 Git。

## 9. 更新和回滚

更新：

```bash
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=200 lottopilot
```

回滚：

1. 将镜像标签改回上一版本，例如 `v1.0.0`。
2. `docker compose pull && docker compose up -d`。
3. 数据库 migration 必须遵循向前兼容策略；涉及不可逆 migration 的发布要提供单独回滚说明。

## 10. 备份

- 每天 `pg_dump`，至少保留 7–30 天。
- 备份 `/app/data` 中的导入文件、导出文件和本地配置附件。
- 数据库备份文件加密后保存到不同磁盘或对象存储。
- 每月执行一次恢复演练。

示例：

```bash
docker exec LottoPilot-postgres pg_dump -U lottopilot -Fc lottopilot > lottopilot-$(date +%F).dump
```

## 11. 生产检查

- GHCR 镜像固定版本。
- APP_SECRET 和数据库密码为随机值。
- PostgreSQL 端口未映射到公网。
- 应用端口只绑定 127.0.0.1。
- HTTPS 和 Secure Cookie 已启用。
- `/docs` 是否公开由配置决定。
- 备份、日志轮转和磁盘告警已配置。
