# 服务�?Docker 部署速查

适用路径：GitHub Actions 构建镜像 �?GHCR �?服务�?Compose�?

## 1. 前置

- 服务器已安装 Docker �?Compose 插件
- 已有可用域名或公�?IP（可�?HTTPS 反代�?
- GitHub 仓库 Actions 已成功产出镜像：

```text
ghcr.io/<owner>/lottopilot:<tag>
```

示例：`ghcr.io/myorg/lottopilot:v1.0.0` �?`...:edge`

## 2. 登录 GHCR（包�?private 时必须）

```bash
# 使用�?read:packages 权限�?PAT
echo "$GHCR_TOKEN" | docker login ghcr.io -u <github-username> --password-stdin
```

若将 Package 设为 Public，可跳过登录�?

## 3. 准备目录与配�?

```bash
mkdir -p /opt/lottopilot && cd /opt/lottopilot
# 从仓库拷贝（�?git clone 后使用）�?
# - deploy/baota/docker-compose.yml
# - .env.example

cp .env.example .env
```

编辑 `.env` 至少�?

```env
APP_ENV=production
APP_SECRET_KEY=<长随机串>
APP_PUBLIC_URL=https://your.domain
COOKIE_SECURE=true
POSTGRES_PASSWORD=<强密�?
HOST_PORT=8088
LOTTOPILOT_IMAGE=ghcr.io/xwordsman/lottopilot:latest
TZ=Asia/Shanghai
```

## 4. 启动

```bash
cp deploy/baota/docker-compose.yml docker-compose.prod.yml
# 若当前目录只�?compose 文件�?
# docker compose -f docker-compose.prod.yml up -d

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

## 5. 健康检�?

```bash
curl -fsS "http://127.0.0.1:${HOST_PORT:-8088}/health"
curl -fsS "http://127.0.0.1:${HOST_PORT:-8088}/api/v1/system/ready"
```

期望�?

- `/health`：`success=true`，`data.status=ok`
- `/ready`：`database=ok`，`migrations=ok`（entrypoint 已执�?alembic�?

## 6. 首次使用

1. 浏览器打开 `APP_PUBLIC_URL`
2. 完成 Setup Wizard 创建管理�?
3. 导入或同步开奖数据（�?0 期）
4. �?`docs/MANUAL_ACCEPTANCE_CHECKLIST.md` 勾选服务器验收�?

## 7. 升级

```bash
# 修改 .env �?LOTTOPILOT_IMAGE 到新 tag
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## 8. 备份

```bash
./scripts/backup_pg.sh ./backups
```

详见 `deploy/baota/README.md`�?
