# Lightweight Data Center Management System

A lightweight internal data center management system for managing data centers, areas, racks, devices, network links, and operational records in one place. The system provides a clean web interface, JWT-based administrator authentication, rack U-position validation, CSV/XLSX import and export, and a Three.js 3D view that displays transparent racks, mounted devices, and related device information.

The project is designed for departmental use: simple to deploy, easy to maintain, and suitable for running locally with SQLite or in a virtual machine with Docker Compose and PostgreSQL. Demo data is disabled by default, so production environments start with an empty business database and only the administrator account needs to be initialized manually.


一个供部门内部使用的轻量级数据中心管理系统，管理机房、区域、机柜、设备、网络链路及 3D 可视化信息。

> 文档更新日期：**2026-09-07**

## 技术栈

- 前端：Vue 3 + TypeScript + Element Plus + Three.js
- 后端：FastAPI + SQLAlchemy
- 数据库：本地 SQLite；Docker/虚拟机使用 PostgreSQL
- 鉴权：JWT；当前仅保留管理员 `admin`
- 部署：Docker Compose + Nginx

## 已实现功能

- 机房管理：新增、编辑、查看、停用
- 区域管理：新增、编辑、删除；区域下存在机柜时禁止删除
- 机柜管理：新增、编辑、查看、停用、利用率统计、U 位查看
- 设备管理：新增、编辑、查询、移动、下架、详情、导入导出；设备类型支持通用服务器、GPU服务器、CPU服务器、管理节点等
- U 位校验：防止设备越界和 U 位重叠
- 网络上联：端口、链路和拓扑信息管理
- 首页概览：数量统计、状态分布、近期变更、异常提醒
- 3D 可视化：展示透明机柜、内部设备及对应数据
- 操作日志：记录关键管理操作

### 机柜位置规则

用户只需填写机柜的**行**和**列**，不需要填写 3D 坐标。系统自动计算：

```text
X = (列 - 1) × 2.2
Y = (行 - 1) × 4.0
```

行列用于日常管理；自动生成的 X/Y 仅用于 3D 页面排布。

## 项目结构

```text
.
├── backend/                 # FastAPI 后端
│   ├── app/                 # 配置、模型、路由、业务服务
│   ├── tests/               # pytest 测试
│   ├── sample_data/         # 设备导入示例
│   ├── requirements.txt
│   ├── Dockerfile
│   └── init_db.py
├── frontend/                # Vue 3 前端
├── deploy/nginx/            # Nginx 配置
├── docker-compose.yml
├── .env.example
└── docs/PROJECT_PLAN.md
```

## 登录账号

系统只保留管理员身份。全新数据库不会自动创建固定密码账号：

```text
用户名：admin
密码：首次部署时手动设置
```

## 本地启动（SQLite）

```bash
cd backend
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 init_db.py
```

`init_db.py` 默认只创建表，不创建用户、不写入业务模拟数据。创建管理员：

```bash
python3 -c '
from getpass import getpass
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import User, RoleEnum
with SessionLocal() as db:
    if db.query(User).filter(User.username == "admin").first():
        print("admin 已存在，未修改密码")
    else:
        password = getpass("设置 admin 密码（至少 12 位）: ")
        assert len(password) >= 12, "密码至少 12 位"
        assert password == getpass("再次输入密码: "), "两次密码不一致"
        db.add(User(username="admin", full_name="系统管理员", role=RoleEnum.admin, hashed_password=get_password_hash(password), is_active=True))
        db.commit()
        print("admin 已创建")
'
```

启动后端：

```bash
PYTHONPATH=. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

新开终端启动前端：

```bash
cd frontend
npm install
npm run dev
```

访问：

- 前端：http://localhost:5173
- 后端健康检查：http://localhost:8000/health
- 后端文档：http://localhost:8000/docs

## `.env` 配置提示

项目根目录提供了 `.env.example` 配置模板。首次使用 Docker Compose 或在虚拟机部署时，先复制一份为 `.env`，再根据实际环境修改：

```bash
cp .env.example .env
chmod 600 .env
```

至少检查并设置以下内容：

```dotenv
POSTGRES_PASSWORD=数据库密码
SECRET_KEY=随机JWT密钥
FRONTEND_PORT=8081
SEED_DEMO_DATA=false
```

`.env` 不要提交到 Git 或发送给他人，其中包含数据库密码和 JWT 密钥。

## Docker Compose 部署

以下命令默认在项目根目录执行。Compose 包含：

| 服务 | 作用 | 默认宿主机端口 |
|---|---|---:|
| `db` | PostgreSQL | 5432 |
| `backend` | FastAPI | 8000 |
| `frontend` | Nginx 前端和 `/api/` 代理 | 8081 |

数据库保存在 Docker volume `postgres_data`。默认不写入模拟机房、机柜或设备数据。

### 1. 准备 Docker 和配置

```bash
docker --version
docker compose version
cp .env.example .env
chmod 600 .env
```

编辑 `.env`，生产环境至少修改：

```dotenv
POSTGRES_PASSWORD=生产数据库强密码
SECRET_KEY=随机JWT密钥
SEED_DEMO_DATA=false
```

生成随机密钥：

```bash
openssl rand -hex 32
```

端口可按需修改：

```dotenv
POSTGRES_PORT=5432
BACKEND_PORT=8000
FRONTEND_PORT=8081
```

已有数据卷创建后，修改 `.env` 中的数据库密码不会自动改变数据库内部密码。

### 2. 检查、构建并启动

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

查看日志：

```bash
docker compose logs -f
# 只看后端
docker compose logs -f backend
```

### 3. 初始化管理员

全新 PostgreSQL 不会自动创建 admin。服务启动后执行：

```bash
docker compose exec backend python -c '
from getpass import getpass
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import User, RoleEnum
with SessionLocal() as db:
    if db.query(User).filter(User.username == "admin").first():
        print("admin 已存在，未修改密码")
    else:
        password = getpass("设置 admin 密码（至少 12 位）: ")
        assert len(password) >= 12, "密码至少 12 位"
        assert password == getpass("再次输入密码: "), "两次密码不一致"
        db.add(User(username="admin", full_name="系统管理员", role=RoleEnum.admin, hashed_password=get_password_hash(password), is_active=True))
        db.commit()
        print("admin 已创建")
'
```

### 4. 访问

- 前端：http://服务器IP:8081
- 健康检查：http://服务器IP:8000/health
- OpenAPI：http://服务器IP:8000/docs

生产环境建议只让用户访问前端端口，不对公网开放 5432；如不需要直接调 API，也不要开放 8000。

### 5. 停止、重启、更新

```bash
# 停止但保留数据
docker compose stop
# 启动
docker compose start
# 重启
docker compose restart
# 更新代码后重新构建
git pull
docker compose up -d --build
# 删除容器但保留 volume
docker compose down
```

删除数据库数据（危险）：

```bash
docker compose down -v
```

### 6. 备份与恢复

备份：

```bash
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > backup.sql
```

恢复到空数据库：

```bash
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U dc_user -d dc_manager < backup.sql
```

恢复前必须先备份；普通 SQL 恢复不会自动清理非空数据库的旧数据。

### 7. 常见问题

```bash
# 服务和健康状态
docker compose ps
# 数据库日志
docker compose logs db
# 后端日志
docker compose logs backend
```

- 8081 被占用：修改 `.env` 的 `FRONTEND_PORT` 后执行 `docker compose up -d`。
- 前端改动未生效：`docker compose build --no-cache frontend && docker compose up -d frontend`。
- 无法登录：确认已执行管理员初始化命令。
- 数据库连接失败：确认 `db` healthy，且 `.env` 数据库名称、用户、密码一致。

## 在虚拟机上部署

以下以 Ubuntu Server 22.04/24.04 为例。

### 推荐配置

最低：2 vCPU、4 GB 内存、30 GB 磁盘。建议：4 vCPU、8 GB 内存、50 GB SSD。

### 1. 安装 Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl git docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

重新登录 SSH 后检查：

```bash
docker --version
docker compose version
```

### 2. 获取项目

使用 Git：

```bash
sudo mkdir -p /opt/dc-manager
sudo chown "$USER":"$(id -gn)" /opt/dc-manager
git clone <你的仓库地址> /opt/dc-manager
cd /opt/dc-manager
```

没有 Git 仓库时，在本地项目根目录打包并上传：

```bash
tar --exclude='./.env' --exclude='*.db' --exclude='*.db-*' --exclude='./.git' --exclude='node_modules' --exclude='dist' --exclude='__pycache__' -czf /tmp/dc-manager.tar.gz .
scp /tmp/dc-manager.tar.gz 用户名@虚拟机IP:~/
```

虚拟机解压：

```bash
sudo mkdir -p /opt/dc-manager
sudo chown "$USER":"$(id -gn)" /opt/dc-manager
tar -xzf ~/dc-manager.tar.gz -C /opt/dc-manager
cd /opt/dc-manager
```

### 3. 配置和启动

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

至少设置：

```dotenv
POSTGRES_PASSWORD=生产数据库强密码
SECRET_KEY=随机JWT密钥
FRONTEND_PORT=8081
SEED_DEMO_DATA=false
```

启动并检查：

```bash
docker compose config
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

然后执行前文“初始化管理员”的 Docker 命令，局域网访问：

```text
http://虚拟机IP:8081
```

### 4. 防火墙和端口

云安全组建议只开放 TCP 22 和前端端口 8081。启用 UFW：

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8081/tcp
sudo ufw enable
sudo ufw status
```

不要开放 5432。生产环境还建议编辑 `docker-compose.yml`，将数据库和后端只绑定到虚拟机本机：

```yaml
# db ports
- "127.0.0.1:${POSTGRES_PORT:-5432}:5432"
# backend ports
- "127.0.0.1:${BACKEND_PORT:-8000}:8000"
```

修改后：

```bash
docker compose up -d
```

### 5. 开机自动启动

```bash
sudo tee /etc/systemd/system/dc-manager.service > /dev/null <<'SYSTEMD_EOF'
[Unit]
Description=Data Center Manager
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/dc-manager
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
RemainAfterExit=yes
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

sudo systemctl daemon-reload
sudo systemctl enable --now dc-manager
sudo systemctl status dc-manager
```

### 6. 日常维护

```bash
cd /opt/dc-manager
docker compose ps
docker compose logs --tail=100 backend
git pull
docker compose up -d --build
docker compose exec -T db pg_dump -U dc_user -d dc_manager > "backup-$(date +%F).sql"
```

## 数据初始化与测试数据

默认启动只创建数据库表，不导入业务模拟数据。如需在独立测试数据库中生成测试数据：

```bash
cd backend
PYTHONPATH=. python3 init_db.py --seed-demo
```

测试数据脚本：`backend/app/services/seed.py`

设备导入示例：`backend/sample_data/devices_import.csv`

不要在生产数据库执行 `--seed-demo`。

## 导入导出

- 设备页面支持导入 `.csv` / `.xlsx`
- 导出：`GET /api/devices/export/csv`、`GET /api/devices/export/xlsx`

## 测试

```bash
cd backend
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 -m pytest -q
```

## 关键接口

- `POST /api/auth/login`
- `GET/POST/PUT /api/datacenters`
- `POST /api/datacenters/{id}/areas`
- `PUT/DELETE /api/datacenters/areas/{area_id}`
- `GET/POST/PUT /api/racks`
- `GET/POST/PUT /api/devices`
- `POST /api/devices/{id}/move`
- `POST /api/devices/{id}/unmount`
- `GET/POST/PUT/DELETE /api/network/links`
- `GET /api/network/topology`
- `GET /api/overview`
- `GET /api/visualization/layout`
- `GET /api/logs`

## 当前说明

- 本地默认 SQLite，容器和虚拟机部署使用 PostgreSQL
- 仅保留管理员身份 `admin`
- 设备下架后保留历史记录，但不再占用 U 位
- 区域下存在机柜时不能删除区域
- 机柜 3D 坐标根据行列自动生成
- 3D 页面可点击机柜和内部服务器查看数据
- 正式环境应修改密码、限制端口并定期备份
EOF
wc -l README.md

### 设备类型代码

设备管理页面显示中文名称，接口、导入模板和数据库保存英文代码：

| 页面名称 | 代码 |
|---|---|
| 通用服务器 | `server` |
| GPU服务器 | `gpu_server` |
| CPU服务器 | `cpu_server` |
| 管理节点 | `management_node` |
| 交换机 | `switch` |
| 存储 | `storage` |
| 配电单元 | `pdu` |
| 防火墙 | `firewall` |
| 其他 | `other` |

如果使用的是已有 PostgreSQL 数据库，需要先扩展 PostgreSQL 枚举类型，再重启后端：

```sql
ALTER TYPE devicetypeenum ADD VALUE IF NOT EXISTS 'gpu_server';
ALTER TYPE devicetypeenum ADD VALUE IF NOT EXISTS 'cpu_server';
ALTER TYPE devicetypeenum ADD VALUE IF NOT EXISTS 'management_node';
```

不同 PostgreSQL/SQLAlchemy 版本生成的枚举类型名称可能不同。可先查询实际名称：

```sql
SELECT n.nspname AS schema_name, t.typname AS enum_name
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE e.enumlabel IN ('server', 'switch', 'storage');
```

将上面 SQL 中的 `devicetypeenum` 替换为查询到的 `enum_name`。全新数据库直接执行 `docker compose up -d --build` 即可。
