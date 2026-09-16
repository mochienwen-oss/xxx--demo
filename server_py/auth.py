# auth.py —— 鉴权：登录态 token 生成 + FastAPI 依赖（对应 Express 版 server/auth.js）
# require_auth / require_role 是 FastAPI 的「依赖注入」，等价于 Express 的中间件：
# 在路由参数里写 user: dict = Depends(require_auth)，FastAPI 会先执行依赖、再进业务函数。
import secrets

from fastapi import Depends, Header

from db import execute, query_one
from errors import ApiError


def create_token(user_id: int) -> str:
    """生成随机 token（64 位十六进制）并存入 sessions 表。"""
    token = secrets.token_hex(32)
    execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def require_auth(authorization: str = Header(default="")):
    """要求已登录：验证 Authorization: Bearer <token>，把用户挂到返回值上（等价 req.user）。"""
    token = (authorization or "").replace("Bearer ", "")
    if not token:
        raise ApiError(401, "未登录")
    s = query_one("SELECT user_id FROM sessions WHERE token = ?", (token,))
    if not s:
        raise ApiError(401, "登录已失效，请重新登录")
    user = query_one(
        "SELECT id, username, name, role, department, skills, phone FROM users WHERE id = ?",
        (s["user_id"],),
    )
    if not user:
        raise ApiError(401, "用户不存在")
    return user


def require_role(*roles):
    """要求特定角色：返回一个依赖，先过 require_auth 再查角色。"""

    def dep(user: dict = Depends(require_auth)):
        if user["role"] not in roles:
            raise ApiError(403, "无权限执行此操作")
        return user

    return dep
