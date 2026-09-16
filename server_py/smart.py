# smart.py —— 智能引擎：千问大模型（分类/派单，兜底本地规则）+ 智能推荐方案
# 对应 Express 版 smart.js，逻辑逐行翻译，行为保持一致。
import re

import llm
from db import query, query_one

FAULT_RULES = [
    {"type": "电脑故障", "keywords": ["电脑", "计算机", "笔记本", "台式机", "无法开机", "蓝屏", "死机", "黑屏", "卡顿", "卡死", "系统", "软件", "键盘", "鼠标", "显示器"]},
    {"type": "网络故障", "keywords": ["网络", "断网", "wifi", "wi-fi", "无线", "网线", "路由器", "上网", "连不上", "掉线", "网速"]},
    {"type": "打印机故障", "keywords": ["打印机", "打印", "卡纸", "墨盒", "复印", "硒鼓", "传真"]},
    {"type": "空调故障", "keywords": ["空调", "不制冷", "不制热", "漏水", "出风", "温度", "风机"]},
    {"type": "投影设备故障", "keywords": ["投影仪", "投影", "幕布", "电视", "大屏", "led屏"]},
    {"type": "水电故障", "keywords": ["灯", "插座", "水管", "漏水", "跳闸", "停电", "电路", "开关", "灯泡", "电闸", "水龙头"]},
]

_SPLIT = re.compile(r"[,，、\s]+")


def _skills_list(skills: str) -> list[str]:
    return [s for s in _SPLIT.split(skills or "") if s]


def classify_local(description: str, device: str) -> dict:
    """本地规则分类（同步，作为千问不可用时的兜底）：统计命中关键词数，取最高分类型（设备名权重更高）。"""
    desc = (description or "").lower()
    dev = (device or "").lower()
    text = f"{dev} {dev} {desc}"
    best_type, best_score = "其他故障", 0
    scores = []
    for rule in FAULT_RULES:
        score = sum(1 for kw in rule["keywords"] if kw.lower() in text)
        scores.append({"type": rule["type"], "score": score})
        if score > best_score:
            best_score, best_type = score, rule["type"]
    confidence = "高" if best_score >= 3 else ("中" if best_score >= 1 else "低")
    return {"type": best_type, "score": best_score, "confidence": confidence, "scores": scores}


async def classify(description: str, device: str) -> dict:
    """智能分类主入口：优先千问大模型，未配置 / 失败则回退本地规则。"""
    r = await llm.classify(description, device)
    return r if r else classify_local(description, device)


def extract_keywords(description: str) -> str:
    """从描述中抽取命中关键词（方案入库时自动标注）。"""
    text = (description or "").lower()
    found = []
    for rule in FAULT_RULES:
        for kw in rule["keywords"]:
            if kw.lower() in text and kw not in found:
                found.append(kw)
    return ",".join(found)


def recommend(description: str, fault_type: str) -> list[dict]:
    """智能推荐：关键词重合度 + 类型匹配打分，取 Top3。"""
    text = (description or "").lower()
    rows = query("SELECT * FROM knowledge")
    scored = []
    for r in rows:
        kws = [k for k in _SPLIT.split(r.get("keywords") or "") if k]
        score = sum(2 for kw in kws if kw.lower() in text)
        if r.get("fault_type") == fault_type:
            score += 1
        if score > 0:
            scored.append({**r, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:3]


def list_workers() -> list[dict]:
    """取所有维修工及其在办工单数。"""
    workers = query("SELECT * FROM users WHERE role = 'worker'")
    out = []
    for w in workers:
        active = query_one(
            "SELECT COUNT(*) c FROM tickets WHERE worker_id = ? AND status IN ('待处理','处理中')", (w["id"],)
        )["c"]
        out.append({**w, "active": active})
    return out


def _safe_worker(w: dict) -> dict:
    """返回给前端的维修工信息：去掉密码哈希等内部字段。"""
    return {k: v for k, v in w.items() if k != "password"}


def dispatch(fault_type: str) -> dict | None:
    """本地派单（同步，兜底 + 管理员智能派单用）：技能匹配 + 在办最少。"""
    scored = []
    for w in list_workers():
        skills = _skills_list(w.get("skills"))
        has_skill = fault_type in skills
        scored.append({**_safe_worker(w), "skills": ",".join(skills), "hasSkill": has_skill, "score": (100 if has_skill else 0) - w["active"]})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[0] if scored else None


async def dispatch_ticket(ticket: dict) -> dict | None:
    """智能派单主入口（维修工端推荐）：优先千问大模型，失败回退本地规则。"""
    workers = list_workers()
    r = await llm.dispatch(ticket, workers)
    if r:
        w = next((x for x in workers if x["name"] == r["name"]), None)
        if w:
            return {**_safe_worker(w), "skills": ",".join(_skills_list(w.get("skills"))), "reason": r["reason"], "source": "llm"}
    return dispatch(ticket.get("fault_type"))
