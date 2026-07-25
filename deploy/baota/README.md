# 宝塔部署说明

## 0. 镜像来源

�?GitHub Actions `CI` 推送到 GHCR�?

```text
ghcr.io/xwordsman/lottopilot:latest
```

�?`.env` 中设置：

```env
LOTTOPILOT_IMAGE=ghcr.io/xwordsman/lottopilot:latest
```

## 1. 前置条件

- 已安�?Docker �?Docker Compose 插件
- 域名已解析，建议开�?HTTPS
- 服务器开�?`HOST_PORT`（默�?8088）或仅本机反�?

## 2. 目录与配�?

```bash
cd /www/wwwroot/LottoPilot
cp .env.example .env
```

至少修改�?

- `APP_SECRET_KEY`：长随机�?
- `POSTGRES_PASSWORD`：数据库密码
- `APP_PUBLIC_URL`：公�?URL（含协议�?
- `COOKIE_SECURE=true`（HTTPS�?
- `HOST_PORT=8088`

镜像部署（推荐生产）�?

```bash
# 使用 deploy/baota/docker-compose.yml
# �?LOTTOPILOT_IMAGE 设为你的 GHCR 镜像，例如：
# LOTTOPILOT_IMAGE=ghcr.io/xwordsman/lottopilot:latest
cp deploy/baota/docker-compose.yml docker-compose.prod.yml
# 编辑 .env 增加 LOTTOPILOT_IMAGE=...
docker compose -f docker-compose.prod.yml up -d
```

源码构建部署�?

```bash
docker compose up -d --build
```

## 3. 宝塔反向代理

- 目标：`http://127.0.0.1:8088`
- 开�?HTTPS
- 转发 Host / X-Forwarded-* �?
- WebSocket 可不开�?

## 4. 健康检�?

- `https://your.domain/health`
- `https://your.domain/api/v1/system/ready`

期望：统一信封 `{success,data,error,request_id}`，`data.status=ok`�?

## 5. 首次使用

1. 打开站点进入 Setup Wizard，创建管理员
2. 登录后进入开奖页，同步或导入 �?0 �?
3. 统计页确认频�?遗漏
4. 推荐页生�?5 �?
5. 回测页跑一段历�?
6. （可选）设置页配�?AI Key（列表只显示脱敏�?

## 6. 备份与恢复演�?

### 备份

```bash
chmod +x scripts/backup_pg.sh scripts/restore_pg.sh
./scripts/backup_pg.sh ./backups
```

生成：`backups/lottopilot_YYYYMMDD_HHMMSS.sql.gz`

### 恢复（会覆盖当前库）

```bash
./scripts/restore_pg.sh ./backups/lottopilot_YYYYMMDD_HHMMSS.sql.gz
```

建议�?

- 每日 cron 备份
- 备份文件保留 �? �?
- 升级前先备份 volume `lottopilot_pgdata`

## 7. 升级

1. 备份数据�?
2. 拉取新镜像标签（�?`git pull` 后重建）
3. `docker compose up -d`
4. 观察 entrypoint 自动 `alembic upgrade head`
5. 检�?`/health` 与登录�?

## 8. 验收对照

详见�?

- `docs/ACCEPTANCE_CRITERIA.md`
- `docs/ACCEPTANCE_STATUS.md`
- `docs/RELEASE_NOTES_v1.0.0.md`
