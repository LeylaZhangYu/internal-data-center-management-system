# 部署与维护指南

[返回 README](../README.md)

本指南适用于 Docker Compose 和 Linux 虚拟机部署。除特别说明外，命令在**项目根目录**执行；示例部署目录为 `/opt/dc-manager`。

- [配置与端口](#配置与端口)
- [启动与访问](#启动与访问)
- [初始化管理员](#初始化管理员)
- [虚拟机部署](#虚拟机部署)
- [更新与日常维护](#更新与日常维护)
- [备份与恢复](#备份与恢复)
- [数据库升级](#数据库升级)
- [部署排错](#部署排错)

## 配置与端口

需要 Docker Engine 和 Compose v2。首次部署复制配置；已有 `.env` 请直接编辑，避免覆盖密码：

```bash
docker --version
docker compose version
cp .env.example .env
chmod 600 .env
```

| 配置 | 示例默认值 | 说明 |
|---|---|---|
| POSTGRES_DB | dc_manager | 数据库名称 |
| POSTGRES_USER | dc_user | 数据库账号，不是网页登录账号 |
| POSTGRES_PASSWORD | dc_password | 正式部署必须替换 |
| SECRET_KEY | please-change-this-secret | JWT签名密钥，正式部署必须替换 |
| FRONTEND_PORT | 8081 | 浏览器入口的宿主机端口 |
| BACKEND_PORT | 8000 | 后端宿主机端口 |
| POSTGRES_PORT | 5432 | 数据库宿主机端口 |
| ACCESS_TOKEN_EXPIRE_MINUTES | 1440 | 登录令牌有效时间 |
| CORS_ORIGINS | * | 跨域配置，按实际访问需求调整 |

分别执行以下命令生成数据库密码和 JWT 密钥，将结果填写到 `.env`：

```bash
openssl rand -hex 24
openssl rand -hex 32
```

当前 Compose **直接拼接数据库 URL**，密码含 `@`、`/`、`#` 等字符可能被错误解析。建议本项目当前配置使用随机十六进制密码；不要简单把编码后的密码同时填给 PostgreSQL 服务。

`docker-compose.yml` 将 `SEED_DEMO_DATA` 固定为 `"false"`，只修改 `.env` 不会开启模拟数据。不要为了创建登录账号开启模拟数据。

当前三个服务都发布宿主机端口。服务器建议只对外提供前端，在 Compose 对应服务的 `ports` 下将数据库和后端改为：

```yaml
# db 的 ports 项
- "127.0.0.1:${POSTGRES_PORT:-5432}:5432"
# backend 的 ports 项
- "127.0.0.1:${BACKEND_PORT:-8000}:8000"
```

前端仍通过 Docker 内部网络访问 `backend:8000`。仅修改宿主机端口不会改变容器内部端口，也不需要修改 Nginx 上游地址。

## 启动与访问

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 backend
curl http://127.0.0.1:8081/health
```

端口有改动时，替换健康检查地址中的端口。数据库应显示 `healthy`，后端日志应出现 `Application startup complete`；健康检查返回 `{"status":"ok"}`。

访问 `http://服务器IP:8081`。后端接口文档默认在 `http://127.0.0.1:8000/docs`（服务器本机）。限制本机绑定后不能从远端直接访问8000，这是预期行为。

第一次部署需继续完成以下账号初始化。只有构建成功不代表后端已经启动成功。

## 初始化管理员

新数据库不会自动创建 `admin`。确认后端启动后执行；密码通过交互输入，不写入命令历史：

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
        password = getpass("设置 admin 密码（至少12位）: ")
        if len(password) < 12 or password != getpass("再次输入密码: "):
            raise SystemExit("密码不足12位或两次输入不一致")
        db.add(User(username="admin", full_name="系统管理员", role=RoleEnum.admin,
                    hashed_password=get_password_hash(password), is_active=True))
        db.commit()
        print("admin 已创建")
'
```

已有账号时保留原密码。页面不提供默认密码，也不预填登录凭据。

## 虚拟机部署

### 准备环境

以下为 Ubuntu 虚拟机示例。资源可从2 vCPU、4GB内存、30GB磁盘起步，按数据量和构建负载调整；这不是容量承诺。

安装 Docker 与 Compose v2 后，确认 `docker compose version` 可用。若使用 Ubuntu 仓库且提供相应软件包：

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-v2
sudo systemctl enable --now docker
```

若仓库没有 Compose v2 包，使用系统对应的 Docker 官方安装步骤，不混用两套 Docker 软件源。后续命令可加 `sudo`；如将用户加入 `docker` 组，需重新登录，且该组具有高权限。

### 上传项目

Git 和打包上传两种方式选一种。先准备目录：

```bash
sudo mkdir -p /opt/dc-manager
sudo chown "$USER":"$(id -gn)" /opt/dc-manager
```

有 Git 仓库时，替换占位符：

```bash
git clone <你的仓库地址> /opt/dc-manager
```

没有 Git 仓库时，在本地项目根目录打包：

```bash
tar --exclude='.env' --exclude='.venv' --exclude='venv' --exclude='*.db' --exclude='*.db-*' --exclude='*.bak' --exclude='.git' --exclude='node_modules' --exclude='dist' --exclude='__pycache__' -czf /tmp/dc-manager.tar.gz .
scp /tmp/dc-manager.tar.gz 用户名@虚拟机IP:~/
```

在虚拟机解压：

```bash
tar -xzf ~/dc-manager.tar.gz -C /opt/dc-manager
cd /opt/dc-manager
```

然后按本指南的[配置与端口](#配置与端口)、[启动与访问](#启动与访问)、[初始化管理员](#初始化管理员)顺序操作，无需重复创建 Python 虚拟环境。

### 网络与开机自启

给虚拟机分配可访问的固定地址。桥接网络可直接访问虚拟机IP；NAT环境需配置宿主机端口转发。云安全组应放行 SSH 和前端端口，限制来源范围。

如使用 UFW，启用前先放行 SSH，避免断开管理连接：

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8081/tcp
sudo ufw enable
sudo ufw status
```

Docker 发布端口与防火墙需一起检查，不要仅依赖 UFW 限制数据库访问；按前文绑定127.0.0.1。需要 HTTPS 时，在前端前增加配置证书的反向代理或负载均衡。

当前 Compose 没有容器重启策略。可以通过 systemd 在虚拟机开机时拉起服务。先确认 `command -v docker` 的输出；若不是 `/usr/bin/docker`，修改下面路径：

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

这是开机拉起服务，不是进程健康监控。需要容器退出后自动恢复时，可另外为各服务配置 `restart: unless-stopped`。

## 更新与日常维护

更新前备份数据库，保留原 `.env`、部署目录和 Compose 项目名。上传更新代码或在 Git 工作区无冲突时拉取，然后执行：

```bash
docker compose up -d --build backend frontend
docker compose ps
docker compose logs --tail=100 backend
```

仅修改后端 Python 文件通常可以复用依赖构建层，不必每次 `--no-cache`。

| 操作 | 命令 | 数据影响 |
|---|---|---|
| 停止 / 启动 | `docker compose stop` / `docker compose start` | 保留数据 |
| 重启后端 | `docker compose restart backend` | 不应用新的环境变量配置 |
| 应用配置变更 | `docker compose up -d` | 按变化重建容器，保留数据卷 |
| 看日志 | `docker compose logs --tail=100 backend` | 只读 |
| 移除容器 | `docker compose down` | 保留命名数据卷 |
| 移除容器及数据卷 | `docker compose down -v` | **永久删除数据库，只用于明确要清空的环境** |

数据卷实际名称通常为 `<项目名>_postgres_data`，更换目录或项目名可能连到新的空卷。中文目录遇到 `project name must not be empty` 时，可首次部署使用 `docker compose -p dc-manager ...`；一旦使用，以后的命令保持相同项目名，不要随意切换。

## 备份与恢复

### PostgreSQL

备份时变量在数据库容器内展开，不需要把 `.env` 加载进宿主 Shell：

```bash
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "backup-$(date +%F-%H%M%S).sql"
```

检查命令退出码和备份文件，备份含业务数据，应安全存放。恢复前停止业务写入并备份目标环境；以下示例要求目标数据库**已创建且为空**，替换实际用户名、库名：

```bash
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U dc_user -d dc_manager < backup.sql
```

这不是覆盖恢复命令，直接导入非空库会有表结构或数据冲突。恢复后启动后端，检查健康状态、登录及已有数据。

### SQLite

停止本地后端后，备份 `backend/datacenter.db`。不要把数据库或自动升级生成的 `.bak` 文件提交到代码仓库；跨数据库类型迁移不等于复制文件。

## 数据库升级

### 设备可选字段

新版后端启动时自动检查并放宽资产编号、型号的非空约束，空白字段保存为 `NULL`；保留非空数据和唯一性约束。升级前备份数据库，暂停其他后端实例写入。

- PostgreSQL：当前账号需要设备表的 `ALTER TABLE` 权限。
- SQLite：旧表升级前在同目录生成 `*.before-device-optionals-*.bak`，目录需可写且有足够空间；保留记录、索引及关联。
- 升级具有幂等性，再次启动无需重复重建表。

### PostgreSQL 设备类型枚举

已有数据库若缺少新增类型，先检查 `devices.device_type` 使用的枚举名称：

```sql
SELECT udt_schema, udt_name
FROM information_schema.columns
WHERE table_name = 'devices' AND column_name = 'device_type';
```

确认使用默认 `devicetypeenum` 后执行；名称不同则替换为实际的 schema 和类型名：

```sql
ALTER TYPE devicetypeenum ADD VALUE IF NOT EXISTS 'gpu_server';
ALTER TYPE devicetypeenum ADD VALUE IF NOT EXISTS 'cpu_server';
ALTER TYPE devicetypeenum ADD VALUE IF NOT EXISTS 'management_node';
```

提交变更后再使用新类型。新建数据库已包含这些类型，无需手工执行。

## 部署排错

### 数据库密码或连接地址错误

`failed to resolve host 'xxx@db'` 通常是密码特殊字符被拼入 URL 后产生解析问题；`password authentication failed` 表示连接已到达数据库，但认证失败。

已有数据卷不会因 `.env` 改密码而自动更新库内密码。需要改密码时，先使用可用数据库账号进入容器内 psql：

```bash
docker compose exec db psql -U dc_user -d dc_manager
```

在 psql 内交互修改密码（必要时登录需输入旧密码）：

```text
\password dc_user
\q
```

把 `.env` 的 `POSTGRES_PASSWORD` 同步为相同密码，然后用 `docker compose up -d backend` 应用配置；只执行 `restart` 不会刷新容器环境变量。不要用删除数据卷的方式解决已有业务数据的密码问题。

### 端口或代理错误

- 8081被占用：修改 `FRONTEND_PORT` 后 `docker compose up -d frontend`。
- 8000/5432被占用：修改对应宿主机端口，容器内部仍使用8000/5432。
- 本地 Vite 请求失败：检查后端 `/health`，确认 `frontend/vite.config.ts` 指向正确的 `127.0.0.1:端口`。
- 云端访问失败：同时检查服务状态、监听地址、端口映射、安全组、防火墙和 NAT 转发。

### 镜像构建或代码未更新

当前前端锁定 TypeScript、vue-tsc，并显式依赖 `@vue/devtools-api`；Dockerfile 使用 `npm install --legacy-peer-deps --include=optional`。请同步 `package.json`、`package-lock.json` 和 Dockerfile，不能只上传页面文件。

```bash
docker compose build frontend backend
docker compose up -d frontend backend
```

确认最新文件已上传后，确实需要排除缓存时再使用 `docker compose build --no-cache frontend`。不要把 `@vue/devtools-api` 加入打包 external 来掩盖依赖缺失。

### 登录或新接口不可用

- 首次部署按本指南创建 admin，使用自行设置的密码。
- 密钥、数据库或运行实例变化后，旧 JWT 可能失效，需要重新登录。
- 新增启用、删除、导入等接口返回404：检查运行后端的 `/docs`，确认镜像含最新路由代码。
- 后端启动失败时先读 `docker compose logs --tail=100 backend`；不要只看前端构建成功信息。
