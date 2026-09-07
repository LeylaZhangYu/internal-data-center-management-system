# 技术架构、数据库设计与开发计划

## 技术架构
- 前端：Vue 3 + TypeScript + Element Plus + Pinia + Vue Router + Three.js
- 后端：FastAPI + SQLAlchemy + JWT 鉴权
- 数据库：PostgreSQL（Docker Compose 运行），本地开发默认 SQLite
- 部署：Docker Compose（PostgreSQL + FastAPI + Nginx 前端）

## 核心数据模型
- `data_centers`：机房主表
- `areas`：机房下的区域，包含行列信息
- `racks`：机柜，关联机房和区域，记录位置、朝向和总 U 数
- `devices`：设备，记录资产、型号、IP、U 位与服务器配置
- `device_placement_history`：上架、移动、下架历史
- `administrators` + `device_admin_association`：管理员与设备多对多
- `device_ports`：设备端口
- `network_links`：端口间链路关系
- `users`：系统登录用户，当前仅保留管理员角色 `admin`
- `audit_logs`：关键操作审计日志

## 开发计划
1. 初始化前后端工程、目录结构、配置、Docker Compose
2. 优先完成机房 / 区域 / 机柜 / U 位 / 设备管理与校验；机柜 3D 坐标由行列自动生成
3. 完成管理员、网络上联、角色权限、操作日志、导入导出
4. 实现首页概览与 3D 机房可视化联动
5. 编写测试并在本地与 Docker Compose 下验证运行
