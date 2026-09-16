# routers/auth.py —— 登录 / 登出 / 当前用户（对应 Express 版 routes/auth.js）
from typing import Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from auth import create_token, require_auth
from db import execute, query_one
from errors import ApiError
from security import verify_password

router = APIRouter()


class LoginBody(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


@router.post("/login")
def login(body: LoginBody):
    if not body.username or not body.password:
        raise ApiError(400, "请输入用户名和密码")
    user = query_one("SELECT * FROM users WHERE username = ?", (body.username,))
    if not user or not verify_password(body.password, user["password"]):
        raise ApiError(401, "用户名或密码错误")
    token = create_token(user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "name": user["name"],
            "role": user["role"],
            "department": user["department"],
            "skills": user["skills"],
        },
    }


@router.post("/logout")
def logout(authorization: str = Header(default=""), user: dict = Depends(require_auth)):
    token = (authorization or "").replace("Bearer ", "")
    execute("DELETE FROM sessions WHERE token = ?", (token,))
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(require_auth)):
    return user
