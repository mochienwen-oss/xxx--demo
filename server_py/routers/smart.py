# routers/smart.py —— 智能能力接口（对应 Express 版 routes/smart.js）
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import smart
from auth import require_auth
from db import query_one
from errors import ApiError

router = APIRouter()


class ClassifyBody(BaseModel):
    description: Optional[str] = None
    device: Optional[str] = None


class RecommendBody(BaseModel):
    description: Optional[str] = None
    # 注意：字段名与前端请求一致（camelCase faultType）
    faultType: Optional[str] = None


@router.post("/classify")
async def classify(body: ClassifyBody, user: dict = Depends(require_auth)):
    return await smart.classify(body.description, body.device)


@router.post("/recommend")
def recommend(body: RecommendBody, user: dict = Depends(require_auth)):
    return smart.recommend(body.description, body.faultType)


@router.get("/dispatch/{ticket_id}")
async def dispatch_ticket(ticket_id: int, user: dict = Depends(require_auth)):
    t = query_one("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not t:
        raise ApiError(404, "工单不存在")
    return await smart.dispatch_ticket(t)
