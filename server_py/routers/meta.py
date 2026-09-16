# routers/meta.py —— 设备 / 维修工 / 统计看板（对应 Express 版 routes/meta.js）
from fastapi import APIRouter, Depends

import smart
from auth import require_auth, require_role
from db import query, query_one

router = APIRouter()


@router.get("/devices")
def devices(user: dict = Depends(require_auth)):
    return query("SELECT * FROM devices ORDER BY id")


@router.get("/workers")
def workers(user: dict = Depends(require_auth)):
    return query("SELECT id, name, skills, phone FROM users WHERE role = 'worker' ORDER BY id")


# 常见问题（故障）类型字典：与智能分类规则同源，末尾兜底「其他故障」
@router.get("/fault-types")
def fault_types(user: dict = Depends(require_auth)):
    return [r["type"] for r in smart.FAULT_RULES] + ["其他故障"]


@router.get("/stats")
def stats(user: dict = Depends(require_role("admin"))):
    total = query_one("SELECT COUNT(*) c FROM tickets")["c"]
    completed = query_one("SELECT COUNT(*) c FROM tickets WHERE status = '已完成'")["c"]
    by_status = query("SELECT status, COUNT(*) c FROM tickets GROUP BY status")
    avg_rating = query_one("SELECT AVG(rating) a FROM tickets WHERE rating IS NOT NULL")["a"]
    return {
        "total": total,
        "completed": completed,
        "rate": round(completed / total * 100) if total else 0,
        "byStatus": by_status,
        "avgRating": round(avg_rating * 10) / 10 if avg_rating else None,
    }
