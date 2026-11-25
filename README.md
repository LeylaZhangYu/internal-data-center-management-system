# Lightweight Data Center Management System

A lightweight internal platform for managing data centers, areas, racks, devices, and network connections. Built with Vue 3, FastAPI, and Three.js, it provides asset management, spreadsheet import/export, rack capacity tracking, and interactive 3D views of physical layouts and network topology.

Run locally with SQLite or deploy with Docker Compose and PostgreSQL. Business demo data is disabled by default, and the administrator account is initialized manually.

一个供部门内部使用的数据中心管理平台，覆盖空间、设备资产、网络连接和操作记录。

## 目录

- [项目概览](#项目概览)
- [本地开发启动](#本地开发启动)
- [Docker 与虚拟机部署](#docker-与虚拟机部署)
- [使用说明](#使用说明)
- [导入与导出](#导入与导出)
- [开发与验证](#开发与验证)
- [常见问题](#常见问题)

详细部署、自启、备份、恢复及升级说明见 [部署与维护指南](docs/DEPLOYMENT.md)。

## 项目概览

| 模块 | 功能 |
|---|---|
| 首页概览 | 机房、机柜、设备统计，状态分布、异常提醒与近期变更 |
| 机房与区域 | 机房新增、编辑、启停和删除；区域新增、编辑、删除 |
| 机柜管理 | 机柜维护、启停、删除、U 位占用和利用率；Excel 批量导入 |
| 设备管理 | 设备维护、查询、移动、下架、详情；CSV/XLSX 导入导出 |
| 服务器管理员 | 维护设备责任人及联系信息，一个设备可关联多名责任人 |
| 网络上联 | 维护端口、链路、带宽和 VLAN，校验端口占用 |
| 3D 可视化 | 按机房、区域查看机柜布局及内部设备 U 位 |
| 3D 网络拓扑 | 根据已录入端口连接展示设备分层及跨机房连接 |
| 操作日志 | 查看关键管理操作记录 |

**技术栈**：Vue 3、TypeScript、Element Plus、Three.js；FastAPI、SQLAlchemy、JWT；SQLite / PostgreSQL；Docker Compose、Nginx。

**账号与数据**：仅保留 `admin` 登录身份。新数据库默认没有登录账号和模拟业务数据，需手动创建管理员。“服务器管理员”是设备责任人资料，与登录账号不同。

## 本地开发启动

适合开发和本机调试，使用 SQLite。以下以 macOS / Linux 为例；准备 Python（建议与后端镜像一致使用 3.11）、Node.js 20 和 npm。

### 1. 创建虚拟环境并安装依赖

在**项目根目录**执行：

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

`.venv` 用于隔离项目依赖。创建前确认 `python3` 指向预期版本；也可明确使用 `python3.11 -m venv .venv`。不要复制其他机器的虚拟环境。

后续命令均在激活该环境后执行。新开终端需重新激活，或直接使用项目中的 `.venv/bin/python`。项目使用 Pydantic 1，约束已写在 `requirements.txt` 中，不要直接用安装了 Pydantic 2 的 Conda `base` 启动。

### 2. 初始化数据库及管理员

```bash
cd backend
PYTHONPATH=. python init_db.py
```

默认数据库为**当前工作目录**下的 `datacenter.db`，请始终从 `backend` 目录启动，避免误用项目根目录中的另一份数据库。初始化不会清空已有数据；旧库约束升级说明见[数据库升级](docs/DEPLOYMENT.md#数据库升级)。

首次使用，在同一终端创建 `admin`，密码交互输入且不回显：

```bash
python -c '
from getpass import getpass
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import User, RoleEnum
with SessionLocal() as db:
    if db.query(User).filter(User.username == "admin").first():
        print("admin 已存在，未修改密码")
    else:
        password = getpass("设置 admin 密码（至少12位）: ")
        if len(password) < 12 or password != getpass("再次输入密码: "):
            raise SystemExit("密码不足12位或两次输入不一致")
        db.add(User(username="admin", full_name="系统管理员", role=RoleEnum.admin,
                    hashed_password=get_password_hash(password), is_active=True))
        db.commit()
        print("admin 已创建")
'
```

### 3. 启动后端

仍在 `backend` 目录：

```bash
PYTHONPATH=. python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

看到 `Application startup complete` 后，在另一个终端检查：

```bash
curl --noproxy '*' http://127.0.0.1:8000/health
```

应返回 `{"status":"ok"}`。

### 4. 启动前端

新开终端，在**项目根目录**执行：

```bash
cd frontend
npm install --legacy-peer-deps --include=optional
npm run dev
```

| 入口 | 本地默认地址 |
|---|---|
| 页面 | `http://127.0.0.1:5173` |
| 后端健康检查 | `http://127.0.0.1:8000/health` |
| API 文档 | `http://127.0.0.1:8000/docs` |

前端开发代理将 `/api`、`/health` 转发至 `127.0.0.1:8000`。修改本地后端端口时，需同步修改 `frontend/vite.config.ts`。Docker 的 `FRONTEND_PORT` 不控制 Vite 端口。

**本地配置文件**：后端按启动目录读取 `.env`，从 `backend` 启动时读取 `backend/.env`；项目根目录的 `.env.example` 主要用于 Compose。若需定制本地后端，可在 `backend/.env` 设置 `SECRET_KEY`、`DATABASE_URL` 等，保持 `SEED_DEMO_DATA=false`。环境变量优先于配置文件。

## Docker 与虚拟机部署

适合服务器持续运行，使用 PostgreSQL。容器安装依赖，不需要宿主机的 Python 虚拟环境或 Node.js。

在**项目根目录**准备配置（已有 `.env` 时不要覆盖）：

```bash
docker --version
docker compose version
cp .env.example .env
chmod 600 .env
```

修改 `.env` 中的 `POSTGRES_PASSWORD`、`SECRET_KEY`，检查端口，再启动：

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 backend
```

| 服务 | 默认宿主机端口 | 作用 |
|---|---:|---|
| frontend | 8081 | Nginx 提供页面，并代理后端请求 |
| backend | 8000 | FastAPI |
| db | 5432 | PostgreSQL |

访问 `http://服务器IP:8081`。**首次部署还需创建 admin**，具体见[容器管理员初始化](docs/DEPLOYMENT.md#初始化管理员)。

部署前请阅读[部署与维护指南](docs/DEPLOYMENT.md)，其中包含配置规则、虚拟机上传代码、端口限制、开机自启、备份恢复和升级步骤。SQLite 数据不会自动迁入 PostgreSQL。

## 使用说明

### 推荐录入顺序

1. 创建机房，在该机房下添加区域。
2. 创建机柜，选择所属机房和区域，填写行列位置及总 U 数。
3. 添加服务器管理员资料。
4. 添加设备，选择机房、机柜、起始 U 位和责任人。
5. 维护设备端口和网络上联，查看空间布局及网络拓扑。

### 位置、字段与删除规则

- **机柜行列**是区域中的布局位置；3D 坐标自动计算，无需手工填写：`X=(列−1)×2.2`、`Y=(行−1)×4.0`。已有保存坐标不会仅因公式变更自动重算。
- **设备安装位置**显示“机柜编号 / U 位范围”，例如 `A01 / U5–U6` 表示从第5个U位起占用2U。
- **资产编号、型号、IP地址**可留空；填写资产编号或 IP 后需保持唯一。页面其他必填项以红色星标提示。
- 设备下架保留设备及历史记录，释放 U 位。停用机房或机柜可通过“启用”恢复。
- **删除机房会连同下属区域、机柜及机柜中的设备一起删除；删除机柜会删除其中设备。** 页面会先弹出确认。区域下有机柜时禁止直接删除区域。

### 设备类型

页面显示中文及英文代码，导入文件的设备类型使用以下代码：

| 名称 | 代码 | 名称 | 代码 |
|---|---|---|---|
| 通用服务器 | `server` | GPU服务器 | `gpu_server` |
| CPU服务器 | `cpu_server` | 管理节点 | `management_node` |
| 交换机 | `switch` | 存储 | `storage` |
| 配电单元 | `pdu` | 防火墙 | `firewall` |
| 其他 | `other` | | |

设备状态代码：`planned`、`active`、`standby`、`maintenance`、`retired`、`off_shelf`。具体填写说明也包含在 Excel 模板中。

### 两种 3D 视图

| 页面 | 用途与范围 |
|---|---|
| 3D可视化 | 选择机房/区域，查看机柜、容量、设备 U 位；支持搜索、选中设备、聚焦机柜及视角切换 |
| 3D网络拓扑 | 按设备类型分层展示已保存的端口连接；支持机房/类型筛选、搜索和对端追踪 |

- 空机房也可选择；不同区域以独立地台展示，区内保留已录入坐标和机柜朝向。
- 机柜视图排除已下架设备；网络拓扑保留未上架和未连接设备。单机房拓扑保留直接连接的外部设备并标注“外部”。
- 链路状态来自录入数据。分层不代表核心/接入角色，流动动画不代表实时流量或方向。
- 页面进入或点击刷新时读取数据。历史异常链路会从视图跳过，不会删除原始记录。
- 需要浏览器支持 WebGL；不可用时仍可通过侧栏查看详情。

## 导入与导出

### 机柜 Excel 批量导入

在机柜管理页下载标准模板，填写后上传 `.xlsx`。最多 **1000 条、5MB**，不支持旧版 `.xls` 或单元格公式。

模板包含“机柜导入模板”“填写说明”“机房区域参考”，没有模拟机柜；参考表是下载时已有机房和区域的快照。

| 表头 | 规则 |
|---|---|
| 机房ID、区域ID、机柜编号 | 必填；机房和区域须存在且启用，区域须属于该机房；同机房内机柜编号唯一 |
| 行、列 | 正整数，默认1 |
| 朝向 | 北向/南向/东向/西向或对应英文，默认北向 |
| 总U数 | 正整数，默认42 |
| 状态 | 启用/停用、true/false或1/0，默认启用 |
| 备注 | 选填 |

支持标准中文表头和对应英文字段名。机房/区域填写系统数字 ID，不是名称；如 `001` 的机柜编号请按文本填写。

导入只新增、不覆盖，逐行保存。结果显示成功数、失败数及 Excel 行号；**只重新导入修正后的失败行**，不要重复导入已成功记录。

### 设备导入导出

设备管理页支持 CSV/XLSX 导入、导出及模板下载，标准表头为中文，导入兼容原英文表头。Excel 模板附填写说明，不含模拟设备。

- 导入必填：设备名称、设备类型；资产编号、型号、IP地址可留空。
- 机柜填写数字 ID；上架时需同时填写机柜 ID 和起始 U 位，且不得越界或重叠。
- 多个管理员 ID 或端口名使用 `|` 分隔。
- 导入用于新增，不覆盖已有设备。没有资产编号的行也会新建设备，请勿重复导入。
- 历史示例文件：`backend/sample_data/devices_import.csv`，不要误导入正式库。

## 开发与验证

### 目录结构

```text
backend/
  app/core/             配置、鉴权、数据库及兼容升级
  app/models/           数据模型
  app/schemas/          请求与响应模型
  app/routers/          接口
  app/services/         业务逻辑、表格导入导出
  tests/                后端测试
  init_db.py            初始化表及兼容升级
frontend/
  src/components/       导航、3D场景组件
  src/views/            页面
  src/styles/           分页面样式
  src/theme.css         通用主题
  tests/                拓扑与布局测试
deploy/nginx/           容器前端反向代理
docs/DEPLOYMENT.md      部署与维护指南
docs/PROJECT_PLAN.md    架构与早期开发计划
```

### 验证命令

项目根目录、已安装依赖后：

```bash
# 后端测试使用独立测试数据库
(cd backend && ../.venv/bin/python -m pytest tests -q)

# 前端逻辑测试与生产构建
npm --prefix frontend run test:topology
npm --prefix frontend run build
```

### 测试数据与接口

正常启动不生成模拟数据。仅在**独立测试数据库**中运行 `python init_db.py --seed-demo`（`backend` 目录）；已有任意用户时该脚本直接退出，不会补充模拟数据。

完整接口以运行服务的 `/docs` 为准，常用入口如下：

| 功能 | 接口 |
|---|---|
| 登录 / 当前用户 | `POST /api/auth/login`、`GET /api/auth/me` |
| 机房 / 区域 | `/api/datacenters`、`/api/datacenters/{id}/areas`、`/api/datacenters/areas/{area_id}` |
| 机柜 / 设备 | `/api/racks`、`/api/devices` |
| 机柜模板 / 导入 | `GET /api/racks/template/xlsx`、`POST /api/racks/import` |
| 设备模板 / 导入 / 导出 | `/api/devices/template/{csv或xlsx}`、`POST /api/devices/import`、`/api/devices/export/{csv或xlsx}` |
| 网络连接 | `/api/network/links`、`/api/network/topology` |
| 3D 场景 | `GET /api/visualization/layout`、`GET /api/visualization/network` |
| 概览 / 日志 | `GET /api/overview`、`GET /api/logs` |

## 常见问题

| 现象 | 优先检查 |
|---|---|
| `BaseSettings has been moved` | 用错 Python 环境；激活项目 `.venv`，按 requirements 安装 Pydantic 1，不要修改 Conda base |
| 编辑器无法解析 FastAPI/openpyxl | 选择项目根目录 `.venv/bin/python`，确认运行与编辑器使用相同解释器 |
| Vite `socket hang up` / `ECONNRESET` | 先检查 `127.0.0.1:8000/health`；代理目标应为 `127.0.0.1`，避免 localhost 被异常解析 |
| 登录失败或 `Could not validate credentials` | 确认 admin 已初始化；令牌失效后重新登录，检查是否更换密钥、数据库或后端地址 |
| 新功能提示 `Not Found` | 确认前后端代码均已更新，后端重启或镜像重新构建后检查 `/docs` |
| Docker 端口冲突、密码错误、构建失败 | 参阅[部署排错](docs/DEPLOYMENT.md#部署排错) |

部署到服务器后看不到本地数据时，先确认使用的数据库；本地 SQLite 与容器 PostgreSQL 是独立的数据源。
