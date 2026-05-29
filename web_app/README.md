# Grid Tender Web App

局域网南网招标看板第一版。

## 结构

- `backend/`: FastAPI + psycopg 3 连接池，只读 PostgreSQL，同时托管前端静态文件。
- `frontend/`: Vue 3 + Vite + TypeScript + Element Plus。

## 部署前提

- PostgreSQL Docker 容器 `grid-tender-postgres` 已在 `127.0.0.1:5432` 运行。
- Node.js >= 18，Python >= 3.10。

## 一键部署（服务器上）

以下命令在 `/data/web_app` 目录下执行：

### 1. 后端：创建虚拟环境、安装依赖

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 已有 .env.example，直接复制即可
cp .env.example .env
```

`.env` 内容：

```env
DATABASE_URL=postgresql://grid_tender:<DB_PASSWORD>@127.0.0.1:5432/grid_tender
CORS_ORIGINS=["*"]
```

### 3. 前端：安装依赖、构建

```bash
cd frontend
npm install
npm run build
```

产物输出到 `frontend/dist/`，后端会自动托管这个目录。

### 4. 启动后端（生产模式）

```bash
cd backend
PYTHONPATH=. nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 10180 \
  > /tmp/web_app_backend.log 2>&1 &
```

## 访问方式

浏览器打开：

```text
http://172.16.1.101:10180
```

后端同时托管前端页面和 API，无需额外部署前端服务器。

### API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/health` | 健康检查 |
| `GET /api/southern-grid/tenders` | 招标公告列表（支持 `?q=关键词&limit=20&offset=0`） |
| `GET /api/southern-grid/tenders/{id}` | 公告详情（含 blocks、requirements、packages） |
| `GET /api/southern-grid/tenders/{id}/blocks` | 正文块 |
| `GET /api/southern-grid/tenders/{id}/requirements` | 招标要求 |

## 开发模式

开发时前后端分开启动，Vite 开发服务器自带 HMR 和 API 代理。

### 后端（开发）

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端（开发）

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Vite 代理配置（`vite.config.ts`）会把 `/api` 请求转发到 `http://127.0.0.1:8000`，如需改用其他端口请修改 `vite.config.ts` 中的 `server.proxy.target`。

浏览器访问 `http://服务器IP:5173`。

## 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 后端框架 | FastAPI | 0.115.6 |
| 数据库驱动 | psycopg (binary + pool) | 3.2.3 |
| 配置管理 | pydantic-settings | 2.7.1 |
| ASGI 服务器 | uvicorn | 0.34.0 |
| 前端框架 | Vue 3 + TypeScript | |
| 构建工具 | Vite | 6.x |
| UI 组件 | Element Plus | |

## 重部署检查清单

- [ ] PostgreSQL Docker 容器正在运行
- [ ] `backend/.env` 中的 `DATABASE_URL` 正确
- [ ] `pip install -r requirements.txt` 安装完整
- [ ] `npm run build` 构建成功，`frontend/dist/` 存在
- [ ] 端口 10180 未被占用
- [ ] `curl http://127.0.0.1:10180/api/health` 返回 `{"status":"ok"}`
- [ ] 浏览器访问 `http://服务器IP:10180` 看到招标看板

## 故障排查

### 端口被占用

```bash
ss -tlnp | grep 10180
```

如果 10180 被占用，可改用其他端口（同步修改启动命令的 `--port` 参数）。

### 后端报数据库连接错误

```bash
# 确认 PostgreSQL 容器在运行
sudo docker ps | grep grid-tender-postgres

# 确认数据库表存在
sudo docker exec grid-tender-postgres psql -U grid_tender -d grid_tender -c "\dt"

# 确认有数据
sudo docker exec grid-tender-postgres psql -U grid_tender -d grid_tender \
  -c "SELECT count(*) FROM tender_documents WHERE is_latest IS TRUE;"
```

### 前端页面空白

检查浏览器控制台，如果 JS/CSS 返回 404，确认：
- `frontend/dist/` 目录存在
- 后端启动命令的 `PYTHONPATH=.` 指向 `backend/` 目录
- `app/main.py` 中 `FRONTEND_DIST` 路径指向正确的 `frontend/dist/`

### 重启后端

```bash
# 查找并杀掉旧进程
pkill -f "uvicorn app.main:app.*10180"

# 重新启动
cd /data/web_app/backend
PYTHONPATH=. nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 10180 \
  > /tmp/web_app_backend.log 2>&1 &
```
