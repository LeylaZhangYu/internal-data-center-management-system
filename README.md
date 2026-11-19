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

### 1. 创建并激活 Python 虚拟环境

建议在项目根目录创建 `.venv`，将项目依赖与系统 Python 隔离：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

说明：

- `python3 -m venv .venv`：创建项目专用虚拟环境
- `source .venv/bin/activate`：激活虚拟环境；终端前出现 `(.venv)` 表示已生效
- `python -m pip install -r backend/requirements.txt`：在当前虚拟环境中安装后端依赖
- 后续启动后端、初始化数据库和运行测试前，都请保持 `.venv` 已激活

如果看到 `(.venv) (base)`，说明同时激活了虚拟环境和 Conda base。通常不影响使用，但建议退出 Conda base 后再操作：

```bash
conda deactivate
source .venv/bin/activate
```

### 2. 初始化 SQLite 数据库

```bash
cd backend
PYTHONPATH=. python init_db.py
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

### 3. 启动后端

确保当前终端仍显示 `(.venv)`，并在 `backend` 目录执行：

```bash
PYTHONPATH=. python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. 启动前端

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

默认账号：admin / admin123

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

已有数据卷创建后，修改 `.env` 中的数据库密码不会自动改变数据库内部密码；如果要改已有库密码，需要进入 PostgreSQL 执行 `ALTER USER`，否则应恢复原密码。

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
- 数据库报错 `failed to resolve host '123@db'`：说明数据库密码包含 `@` 等 URL 特殊字符，连接串被错误解析。把 `.env` 的 `POSTGRES_PASSWORD` 改为只含字母、数字、下划线或短横线的值，然后执行 `docker compose down`，删除并重建数据库数据卷（见下方说明）或在现有 PostgreSQL 中同步修改密码，再重新启动。

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

### 机柜 Excel 批量导入

机柜管理页提供“Excel 批量导入”和“下载导入模板”。先下载模板，在第一个工作表填写，保存后上传 `.xlsx`（不支持 `.xls`，最多1000条、5MB）。

| 中文表头 | 填写规则 |
|---|---|
| 机房ID、区域ID | 必填数字ID；机房/区域必须已存在且启用，区域必须属于所填机房 |
| 机柜编号 | 必填，同一机房内唯一；如001等编号请以文本填写，最多50字符 |
| 行、列 | 正整数，留空默认1；无需填写X/Y坐标 |
| 朝向 | 北向/南向/东向/西向或north/south/east/west；默认北向 |
| 总U数 | 正整数；默认42 |
| 状态 | 启用/停用或true/false、1/0；默认启用 |
| 备注 | 选填 |

模板附“填写说明”和“机房区域参考”（当前已有数据的快照），主表不包含模拟机柜。
支持对应英文表头 `data_center_id, area_id, code, row_position, column_position, orientation, total_u, is_active, remark`，不支持单元格公式。
导入只新增、不覆盖，逐行提交并记录操作日志；失败行会显示Excel行号及原因，成功行不回滚。仅重新导入修正后的失败行。

接口：`GET /api/racks/template/xlsx`、`POST /api/racks/import`。需要登录，导入仅限管理员。
更新部署时需同时更新前后端；本功能无需新增数据库表或字段。

### 设备导入导出

- 资产编号、型号、IP 地址为选填项；新增、编辑以及 CSV/XLSX 导入均可留空。
- 填写资产编号或 IP 地址时仍需保持唯一；没有资产编号的导入行也会新建设备，请勿重复导入。
- 设备页面支持导入 `.csv` / `.xlsx`
- 导出：`GET /api/devices/export/csv`、`GET /api/devices/export/xlsx`

### 已有数据库升级（设备可选字段）

更新前请备份数据库，暂停其他后端实例的写入，再首次启动新版后端。
启动时会检查并放宽 `devices.asset_number`、`devices.model` 的非空约束，
空白字段按 `NULL` 保存，原有非空数据与唯一性约束保留。

- PostgreSQL：使用当前数据库账号执行 `ALTER TABLE`，该账号需有设备表修改权限。
- SQLite：旧表升级前会在数据库同目录生成 `*.before-device-optionals-*.bak` 备份；
  升级需该目录可写，并保留足够空间存放备份和临时表。不会清空业务数据。
- 升级具有幂等性，完成后再次启动无需重建表。
- SQLite 备份包含业务数据，请妥善保存，不要提交至代码仓库。

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


### 3D 网络拓扑

侧边栏的 **3D网络拓扑** 打开 `/network-topology`，通过需要登录的
`GET /api/visualization/network` 读取数据库中的全部设备、机房位置和端口链路。
进入页面或点击“刷新数据”会重新获取数据，不需要单独维护拓扑副本。

- 按设备类型分为安全设备、网络交换、服务器计算、存储设备、配套与其他五层。
  分层是展示分类，不推断网络核心/接入角色或业务流向。
- 支持机房筛选、设备类型筛选、名称/IP/资产编号/型号/位置搜索。
  单机房视图保留直接连接的外部设备并标注“外部”；搜索用于定位侧栏设备。
- 点击节点或设备列表可突出直连关系，查看型号、状态、IP、U位、管理员及端口、带宽、VLAN。
  点击连接设备可继续查看对端；必要时会取消类型筛选或切回全部机房。
- 仅根据“网络上联”中已保存的端口连接绘制链路；未连接、未上架设备仍可展示。
  链路颜色对应录入的正常/中断/规划中状态，不代表自动监测结果。
- 支持旋转、缩放、平移、全屏、俯视、重置视角、标签开关和流动示意。
  流动动画默认关闭，仅为视觉示意，不代表实时流量或数据方向。
- 不修改数据库结构。现有“3D可视化”继续用于机柜实体布局。
  浏览器需要支持 WebGL；不可用时仍可通过侧栏查看设备与连接详情。

验证命令：在 `frontend` 目录运行 `npm run test:topology` 和 `npm run build`；
在 `backend` 目录运行 `../.venv/bin/python -m pytest tests -q`。

### 3D 机柜空间视图

“3D可视化”采用与网络拓扑一致的深色界面，包含机房/区域筛选、机柜与设备搜索、
U 位容量统计、设备详情、状态灯色、全屏、俯视/正视、聚焦机柜及标签/网格/透明柜体开关。
区域以独立地台分组展示；区内保留已录入机柜坐标，柜体按朝向旋转，设备高度及位置按实际 U 数绘制。
页面通过现有 `/api/visualization/layout` 接口读取数据，无需修改数据库。
状态灯色对应录入状态，不是实时监测。布局计算可在 `frontend` 目录通过
`node --test tests/rack-layout.test.mjs` 验证。
