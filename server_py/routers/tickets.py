# routers/tickets.py —— 工单 CRUD + 状态机流转（对应 Express 版 routes/tickets.js）
# 校验顺序、错误提示、SQL、返回字段均与 JS 版保持一致。
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

import smart
from auth import require_auth, require_role
from db import execute, query, query_one
from errors import ApiError

router = APIRouter()

# 状态机：每个状态允许流转到的下一状态
STATUS = {"PENDING": "待处理", "IN_PROGRESS": "处理中", "DONE": "已完成", "REJECTED": "已驳回"}
FLOW = {
    STATUS["PENDING"]: [STATUS["IN_PROGRESS"], STATUS["REJECTED"]],
    STATUS["IN_PROGRESS"]: [STATUS["DONE"], STATUS["PENDING"]],
    STATUS["REJECTED"]: [],
    STATUS["DONE"]: [],
}


def can_transition(frm: str, to: str) -> bool:
    return to in FLOW.get(frm, [])


TICKET_SELECT = """
SELECT t.*,
  e.name AS employee_name, e.department AS employee_dept,
  COALESCE(NULLIF(t.device_name, ''), d.name) AS device_name,
  w.name AS worker_name
FROM tickets t
LEFT JOIN users e ON e.id = t.employee_id
LEFT JOIN devices d ON d.id = t.device_id
LEFT JOIN users w ON w.id = t.worker_id
"""


def get_ticket(ticket_id: int) -> dict | None:
    return query_one("SELECT * FROM tickets WHERE id = ?", (ticket_id,))


# ---------- 请求体模型 ----------
class TicketBody(BaseModel):
    device_name: Optional[str] = None
    device_id: Optional[int] = None
    description: Optional[str] = None
    image: Optional[str] = None
    fault_type: Optional[str] = None


class ClaimBody(BaseModel):
    worker_id: Optional[int] = None


class CompleteBody(BaseModel):
    solution: Optional[str] = None


class TransferBody(BaseModel):
    worker_id: Optional[int] = None


class RateBody(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None


# ---------- 接口 ----------
# 列表（按角色自动过滤：员工看自己的，维修工看自己+待处理大厅，管理员看全部）
@router.get("")
def list_tickets(
    status: Optional[str] = Query(default=None),
    user: dict = Depends(require_auth),
):
    conds, params = [], []
    if user["role"] == "employee":
        conds.append("t.employee_id = ?")
        params.append(user["id"])
    elif user["role"] == "worker":
        conds.append("(t.worker_id = ? OR t.status = ?)")
        params += [user["id"], STATUS["PENDING"]]
    if status:
        conds.append("t.status = ?")
        params.append(status)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    return query(TICKET_SELECT + where + " ORDER BY t.id DESC", tuple(params))


@router.get("/{ticket_id}")
def get_ticket_detail(ticket_id: int, user: dict = Depends(require_auth)):
    t = query_one(TICKET_SELECT + " WHERE t.id = ?", (ticket_id,))
    if not t:
        raise ApiError(404, "工单不存在")
    return t


# 提交报修（员工，可手动选择问题类型；未选时自动智能分类）
@router.post("")
async def create_ticket(body: TicketBody, user: dict = Depends(require_role("employee"))):
    device_name = body.device_name or ""
    if not body.description:
        raise ApiError(400, "请填写故障描述")
    # 员工手动选择的类型优先；为空时回退智能分类
    fault_type = (body.fault_type or "").strip()
    if not fault_type:
        r = await smart.classify(body.description, device_name)
        fault_type = r["type"]
    ticket_id = execute(
        "INSERT INTO tickets (employee_id, device_id, device_name, fault_type, description, image) VALUES (?,?,?,?,?,?)",
        (user["id"], body.device_id, device_name or None, fault_type, body.description, body.image or None),
    )
    return {"id": ticket_id, "fault_type": fault_type}


# 接单（维修工自接 / 管理员派单）
@router.post("/{ticket_id}/claim")
def claim_ticket(ticket_id: int, body: ClaimBody, user: dict = Depends(require_role("worker", "admin"))):
    t = get_ticket(ticket_id)
    if not t:
        raise ApiError(404, "工单不存在")
    if not can_transition(t["status"], STATUS["IN_PROGRESS"]):
        raise ApiError(400, f"当前状态「{t['status']}」不可接单")

    worker_id = user["id"] if user["role"] == "worker" else body.worker_id
    if not worker_id:
        best = smart.dispatch(t.get("fault_type"))
        if not best:
            raise ApiError(400, "暂无可用维修工")
        worker_id = best["id"]
    execute("UPDATE tickets SET worker_id = ?, status = ? WHERE id = ?", (worker_id, STATUS["IN_PROGRESS"], ticket_id))
    return {"ok": True, "worker_id": worker_id}


# 完成（处理方案自动沉淀到知识库）
@router.post("/{ticket_id}/complete")
def complete_ticket(ticket_id: int, body: CompleteBody, user: dict = Depends(require_role("worker", "admin"))):
    t = get_ticket(ticket_id)
    if not t:
        raise ApiError(404, "工单不存在")
    if user["role"] == "worker" and t["worker_id"] != user["id"]:
        raise ApiError(403, "只能完成自己的工单")
    if not can_transition(t["status"], STATUS["DONE"]):
        raise ApiError(400, f"当前状态「{t['status']}」不可完成")
    solution = (body.solution or "").strip()
    execute(
        "UPDATE tickets SET status=?, solution=?, resolved_at=datetime('now','localtime') WHERE id=?",
        (STATUS["DONE"], body.solution or "", ticket_id),
    )
    if solution:
        execute(
            "INSERT INTO knowledge (fault_type, keywords, solution) VALUES (?,?,?)",
            (t.get("fault_type") or "其他故障", smart.extract_keywords(t.get("description") or ""), solution),
        )
    return {"ok": True}


# 转单（处理中 → 待处理，更换维修工）
@router.post("/{ticket_id}/transfer")
def transfer_ticket(ticket_id: int, body: TransferBody, user: dict = Depends(require_role("worker", "admin"))):
    t = get_ticket(ticket_id)
    if not t:
        raise ApiError(404, "工单不存在")
    if user["role"] == "worker" and t["worker_id"] != user["id"]:
        raise ApiError(403, "只能转自己的工单")
    if not can_transition(t["status"], STATUS["PENDING"]):
        raise ApiError(400, f"当前状态「{t['status']}」不可转单")

    if body.worker_id:
        # 改派：保持处理中，仅更换维修工
        execute("UPDATE tickets SET worker_id = ? WHERE id = ?", (body.worker_id, ticket_id))
    else:
        # 退回待处理：清空维修工
        execute("UPDATE tickets SET status = ?, worker_id = ? WHERE id = ?", (STATUS["PENDING"], None, ticket_id))
    return {"ok": True}


# 驳回（管理员）
@router.post("/{ticket_id}/reject")
def reject_ticket(ticket_id: int, user: dict = Depends(require_role("admin"))):
    t = get_ticket(ticket_id)
    if not t:
        raise ApiError(404, "工单不存在")
    if not can_transition(t["status"], STATUS["REJECTED"]):
        raise ApiError(400, f"当前状态「{t['status']}」不可驳回")
    execute("UPDATE tickets SET status=? WHERE id=?", (STATUS["REJECTED"], ticket_id))
    return {"ok": True}


# 评价（员工本人）
@router.post("/{ticket_id}/rate")
def rate_ticket(ticket_id: int, body: RateBody, user: dict = Depends(require_role("employee"))):
    t = get_ticket(ticket_id)
    if not t:
        raise ApiError(404, "工单不存在")
    if t["employee_id"] != user["id"]:
        raise ApiError(403, "只能评价自己的工单")
    rating = body.rating if body.rating is not None else None
    execute("UPDATE tickets SET rating=?, comment=? WHERE id=?", (rating, body.comment or "", ticket_id))
    return {"ok": True}


# 催办（员工本人）
@router.post("/{ticket_id}/urge")
def urge_ticket(ticket_id: int, user: dict = Depends(require_role("employee"))):
    t = get_ticket(ticket_id)
    if not t:
        raise ApiError(404, "工单不存在")
    if t["employee_id"] != user["id"]:
        raise ApiError(403, "只能催办自己的工单")
    execute("UPDATE tickets SET urge_count = urge_count + 1 WHERE id=?", (ticket_id,))
    return {"ok": True}
