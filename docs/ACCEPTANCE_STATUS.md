# LottoPilot 验收状态

> 更新时间：2026-07-25  
> 判定依据：docs/ACCEPTANCE_CRITERIA.md v1.3  
> 发布路径：**GitHub Actions 构建 → GHCR → 服务器 Docker Compose**（不依赖开发机本地 Docker/测试作为权威证据）

## 1. 全局硬约束

| ID | 状态 | 证据 |
|---|---|---|
| G-01~G-06 | PASS（代码与文档已落地） | 待 Actions + 服务器人工最终确认 |

## 2. Phase 完成度

| Phase | 状态 | 备注 |
|---|---|---|
| 0–7 | PASS（实现齐） | 认证/数据/统计/推荐/回测/AI/UI |
| 8 Release | READY_FOR_CI | 工件齐；待推送 GitHub 由 Actions 构建镜像，服务器编排部署 |

## 3. 发布工件清单

| 工件 | 状态 |
|---|---|
| `Dockerfile` 多阶段 + healthcheck + entrypoint migrate | READY |
| 根目录 `docker-compose.yml`（源码构建） | READY |
| `deploy/baota/docker-compose.yml`（拉镜像） | READY |
| `.github/workflows/ci.yml` | READY |
| `.github/workflows/ci.yml`（QEMU/Buildx/GHCR） | READY |
| `.env.example` | READY |
| 验收标准 v1.3（P8-19/20/21） | READY |

## 4. 权威验证（按用户发布流程）

### 4.1 GitHub Actions（推送后自动）

```text
ci.yml     → offline + backend + frontend + docker build
ci.yml → multi-arch push ghcr.io/<owner>/lottopilot
```

### 4.2 服务器部署（人工）

```text
配置 .env + LOTTOPILOT_IMAGE
docker compose -f deploy/baota/docker-compose.yml up -d
GET /health 与 /api/v1/system/ready
完成 Setup + 人工 9.2
```

### 4.3 开发机本地测试

**非本阶段必选项。** 本地 SQLite/全栈脚本仅开发辅助。

## 5. 发布判定

- **代码与部署工件：已就绪，可推送 GitHub**
- **GitHub 推送：已完成** → https://github.com/Xwordsman/LottoPilot （`main` @ 155133a）
- **下一步：等待 Actions 全绿 + 服务器 Compose 部署 + 人工 9.2**
- **CI 绿 / GHCR 镜像 / 服务器 Compose 健康 / 人工 9.2：待推送后由 Actions 与服务器完成**
- **在上述未完成前，不可宣称生产发布成功**
