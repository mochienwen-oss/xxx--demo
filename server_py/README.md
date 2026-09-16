# server_py —— 智能报修系统后端（FastAPI / Python 版）

由 Express/Node.js 版迁移而来，**接口契约 100% 保持一致，前端零改动**。原 JS 后端 `server/` 已删除，本目录是唯一后端。

## 快速开始

```bash
cd server_py
pip install -r requirements.txt
python main.py            # 或 uvicorn main:app --port 3000
```

- 启动后监听 **3000 端口**，前端 `web` 的 vite 代理无需修改。
- 数据库 `server_py/data/app.db` 已在迁移时从旧库完整导入（含原有工单、知识库、登录会话），无需重新初始化。

## 目录结构与 JS 版对应关系

| FastAPI 版 | Express 版 | 说明 |
|---|---|---|
| `main.py` | `server.js` | 入口：异常契约、挂载路由、生产托管静态 |
| `routers/auth.py` | `routes/auth.js` | 登录 / 登出 / me |
| `routers/tickets.py` | `routes/tickets.js` | 工单 CRUD + 状态机 |
| `routers/smart.py` | `routes/smart.js` | 智能分类 / 推荐 / 派单接口 |
| `routers/meta.py` | `routes/meta.js` | 设备 / 维修工 / 故障字典 / 统计 |
| `auth.py` | `auth.js` | 鉴权：create_token + require_auth/require_role 依赖 |
| `security.py` | `security.js` | 密码哈希（scrypt，参数与 Node 一致） |
| `db.py` | `db.js` | SQLite 建表 + 种子数据 |
| `smart.py` | `smart.js` | 智能引擎：千问优先、本地规则兜底 |
| `llm.py` | `llm.js` | 千问 DashScope 客户端 |

## 关键契约（迁移时保留，前端依赖这些）

1. **URL 与 HTTP 方法不变**：`/api/auth/*`、`/api/tickets/*`、`/api/smart/*`、`/api/devices` 等。
2. **错误字段是 `error`**：所有失败返回 `{"error": "中文提示"}`。FastAPI 默认用 `detail`，已通过 `ApiError` + 全局异常处理器改回 `error`。
3. **身份验证**：`Authorization: Bearer <token>`，token 仍存 `sessions` 表，64 位十六进制。
4. **返回 JSON 字段名不变**：如 `employee_name`、`device_name`、`worker_name`、`{ok: true, worker_id}` 等。

## 大模型（智能分类/派单）配置

与 JS 版相同，二选一：
1. 环境变量 `DASHSCOPE_API_KEY`
2. 在 `server_py/config.json` 写 `{"dashscopeApiKey": "sk-xxx", "model": "qwen-flash"}`

未配置时自动回退本地关键词规则，系统仍可完整运行。
（迁移时已把原配置复制为本目录 `config.json`，`llm.py` 会优先读环境变量 `DASHSCOPE_API_KEY`，其次读本目录 `config.json`。）

## 调试

- 启动后访问 **http://localhost:3000/docs** 打开 FastAPI 交互式 API 文档，可直接点击调试每个接口。
- 前后端断链排查：确认 3000 端口是 Python 服务在听（`netstat -ano | findstr :3000`），前端 Network 面板看请求头是否带 `Authorization`。

## 安全备注（迁移时顺手修正）

- 派单接口返回的维修工信息已去掉 `password` 哈希字段（JS 版会带上，属遗留问题）。
- `config.json` 明文保存了真实 API Key，建议改用环境变量 `DASHSCOPE_API_KEY` 并轮换该 Key。
