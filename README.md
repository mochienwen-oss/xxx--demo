# xxx公司智能报修系统

企业级智能报修管理平台：员工一键报修，AI 自动分类并派单，维修工接单处理，管理员全程掌控，知识库沉淀解决方案并反哺智能分类。

## 功能特性

- **三角色闭环**：员工（提交/催办/评价）、维修工（接单/处理/转派）、管理员（派单/驳回/统计），角色权限由后端依赖注入统一管控
- **AI 智能分类派单**：优先调用通义千问（qwen-flash）对故障描述分类并匹配技能合适的维修工；未配置 API Key 时自动回退到本地规则引擎，系统可完整运行
- **工单状态机**：待处理 → 处理中 → 已完成 / 已驳回，非法状态迁移被后端拦截
- **知识库自学习**：已完成的工单沉淀进 knowledge 表，作为后续分类的参考
- **统一错误契约**：所有接口错误返回 `{ "error": "中文提示" }`，前端统一 Toast 展示

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 前端 UI | Vue 3 + Vite | 组件化页面，`web/src/views/` |
| 前端请求 | 原生 fetch 封装（api.js） | 自动携带 Bearer Token、统一错误处理 |
| 后端接口 | FastAPI + Uvicorn | `server_py/`，端口 3000 |
| 数据库 | SQLite | `server_py/data/app.db`，5 张表 |
| 智能分类 | 通义千问 qwen-flash + 本地规则兜底 | 无 Key 可运行 |

## 项目结构

```
├── server_py/            # FastAPI 后端（Python）
│   ├── main.py           # 入口：路由挂载、异常处理器、静态托管
│   ├── auth.py           # 登录态 Token + 依赖注入（require_auth / require_role）
│   ├── security.py       # 密码哈希（scrypt）
│   ├── db.py             # SQLite 初始化、建表、种子数据
│   ├── llm.py / smart.py # 大模型调用与本地规则引擎
│   ├── routers/          # auth / tickets / smart / meta 接口
│   └── config.example.json  # API Key 配置模板（真实 key 不入库）
└── web/                  # Vue 3 前端
    ├── src/api.js        # 唯一请求出口
    ├── src/views/        # Login / Employee / Worker / Admin 页面
    └── vite.config.js    # 开发代理：/api → localhost:3000
```

## 快速开始

**1. 启动后端**（需要 Python 3.10+）

```bash
cd server_py
pip install -r requirements.txt
python main.py            # 或 uvicorn main:app --port 3000
```

可选：配置智能分类的 API Key

```bash
cp config.example.json config.json
# 编辑 config.json，填入 DashScope API Key（阿里云百炼）
# 不配置也能运行：自动使用本地规则引擎分类
```

**2. 启动前端**（需要 Node.js 18+）

```bash
cd web
npm install
npm run dev               # http://localhost:5173 ，/api 请求自动代理到 3000
```

**3. 生产模式**：先 `npm run build` 生成 `web/dist`，后端检测到该目录后会自动同端口托管前端页面。

## 演示账号

| 角色 | 用户名 / 密码 | 说明 |
|---|---|---|
| 管理员 | admin / admin123 | 派单、驳回、统计 |
| 员工 | chenxiao / 123456 | 提交报修（另有 liuyang、zhaomin、sunlei） |
| 维修工 | zhangwei / 123456 | 接单、处理（另有 liqiang、wangfang） |

## 安全说明

- 真实 API Key 存放于 `server_py/config.json`，已被 `.gitignore` 排除，**不会进入版本库**；仓库内仅提供 `config.example.json` 模板
- 密码使用 scrypt 加盐哈希存储；登录态为随机 64 位十六进制 Token（存 sessions 表）

## 接口文档

启动后端后访问 `http://localhost:3000/docs`（FastAPI 自动生成，可在线调试）。
