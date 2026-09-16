# llm.py —— 千问（阿里云 DashScope）大模型：智能分类 + 智能派单
# 对应 Express 版 llm.js。API Key 配置（优先级从高到低）：
#   1. 环境变量 DASHSCOPE_API_KEY
#   2. 本目录 config.json 的 "dashscopeApiKey" 字段
# 全部未配置 / 调用失败时返回 None，由 smart.py 自动回退本地规则。
import json
import os
import re

import httpx

API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
FAULT_TYPES = ["电脑故障", "网络故障", "打印机故障", "空调故障", "水电故障", "投影设备故障", "其他故障"]

_here = os.path.dirname(os.path.abspath(__file__))


def _load_cfg() -> dict:
    try:
        with open(os.path.join(_here, "config.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_cfg = _load_cfg()
MODEL = _cfg.get("model") or "qwen-flash"


def get_api_key() -> str:
    return os.environ.get("DASHSCOPE_API_KEY") or _cfg.get("dashscopeApiKey") or ""


async def call_qwen(prompt: str) -> str | None:
    """统一调用千问，返回文本内容；未配置 / 失败返回 None。"""
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                API_BASE,
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
                json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
            )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        return None


def parse_json(content: str):
    """容错解析模型返回的 JSON：直接解析，失败则提取 { ... } 子串。"""
    try:
        return json.loads(content)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", content or "")
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


async def classify(description: str, device: str):
    """智能分类：根据设备名 + 故障描述判断故障类型。"""
    prompt = (
        "你是企业报修系统的智能分类助手。请根据「设备名称」和「故障描述」判断故障类型。\n"
        f"故障类型只能从以下选项中选择其一：{'、'.join(FAULT_TYPES)}\n"
        '只输出 JSON，不要输出任何多余文字，格式：{"type":"故障类型","confidence":"高|中|低","reason":"一句话依据"}\n\n'
        f"设备名称：{device or '未提供'}\n"
        f"故障描述：{description or '未提供'}"
    )
    content = await call_qwen(prompt)
    if not content:
        return None
    obj = parse_json(content)
    if not obj or not isinstance(obj.get("type"), str):
        return None
    fault_type = obj["type"] if obj["type"] in FAULT_TYPES else "其他故障"
    confidence = obj.get("confidence") if obj.get("confidence") in ["高", "中", "低"] else "中"
    return {"type": fault_type, "confidence": confidence, "reason": obj.get("reason", ""), "source": "llm"}


async def dispatch(ticket: dict, workers: list[dict]):
    """智能派单：根据工单信息 + 维修工列表，推荐最合适的维修工。"""
    prompt = (
        "你是企业报修系统的智能派单助手。请根据工单信息和维修工列表，推荐最合适的维修工。\n"
        f"工单故障类型：{ticket.get('fault_type') or '其他故障'}\n"
        f"设备名称：{ticket.get('device_name') or '未提供'}\n"
        f"故障描述：{ticket.get('description') or '未提供'}\n"
        "维修工列表（姓名：技能 / 在办工单数）：\n"
        + "\n".join(f"{w['name']}：{w.get('skills') or '通用'} / 在办 {w['active']} 单" for w in workers)
        + '\n\n请只输出 JSON，不要输出任何多余文字，格式：{"worker_name":"维修工姓名","reason":"一句话推荐理由"}'
    )
    content = await call_qwen(prompt)
    if not content:
        return None
    obj = parse_json(content)
    if not obj or not isinstance(obj.get("worker_name"), str):
        return None
    return {"name": obj["worker_name"].strip(), "reason": obj.get("reason", ""), "source": "llm"}
