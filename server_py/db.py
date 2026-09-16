# db.py —— SQLite 初始化、建表、种子数据（Python 标准库 sqlite3）
# 对应 Express 版 db.js（node:sqlite）：同一套表结构、同一批种子数据。
import os
import sqlite3
import threading

from security import hash_password

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "app.db")

# 连接与锁：FastAPI 的同步接口在线程池中执行，需要跨线程安全
_lock = threading.RLock()
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.execute("PRAGMA journal_mode = WAL")


def query(sql: str, params: tuple = ()) -> list[dict]:
    """查询多行，返回 [{列名: 值}, ...]。"""
    with _lock:
        rows = _conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """查询单行，返回 {列名: 值} 或 None。"""
    with _lock:
        row = _conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    """执行写入（自动提交），返回 lastrowid。"""
    with _lock:
        cur = _conn.execute(sql, params)
        _conn.commit()
        return cur.lastrowid


_conn.executescript(
    """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  department TEXT DEFAULT '',
  skills TEXT DEFAULT '',
  phone TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS devices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  location TEXT NOT NULL,
  status TEXT DEFAULT '正常'
);

CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id INTEGER NOT NULL,
  device_id INTEGER,
  fault_type TEXT,
  description TEXT NOT NULL,
  image TEXT,
  status TEXT DEFAULT '待处理',
  worker_id INTEGER,
  solution TEXT,
  rating INTEGER,
  comment TEXT,
  urge_count INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS knowledge (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fault_type TEXT NOT NULL,
  keywords TEXT NOT NULL,
  solution TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
"""
)

# 迁移：设备名改为自由文本输入，为 tickets 补充 device_name 列
try:
    _conn.execute("ALTER TABLE tickets ADD COLUMN device_name TEXT")
    _conn.commit()
except sqlite3.OperationalError:
    pass  # 列已存在，忽略

# 首次运行写入种子数据（与 db.js 完全一致）
if query_one("SELECT COUNT(*) c FROM users")["c"] == 0:
    u = "INSERT INTO users (username, password, name, role, department, skills, phone) VALUES (?,?,?,?,?,?,?)"
    for username, password, name, role, department, skills, phone in [
        ("admin", "admin123", "系统管理员", "admin", "", "", ""),
        ("chenxiao", "123456", "陈晓", "employee", "市场部", "", ""),
        ("liuyang", "123456", "刘洋", "employee", "财务部", "", ""),
        ("zhaomin", "123456", "赵敏", "employee", "研发部", "", ""),
        ("sunlei", "123456", "孙磊", "employee", "人事部", "", ""),
        ("zhangwei", "123456", "张伟", "worker", "", "电脑故障,网络故障", "13800000001"),
        ("liqiang", "123456", "李强", "worker", "", "水电故障,空调故障", "13800000002"),
        ("wangfang", "123456", "王芳", "worker", "", "打印机故障,电脑故障", "13800000003"),
    ]:
        _conn.execute(u, (username, hash_password(password), name, role, department, skills, phone))

    d = "INSERT INTO devices (name, location) VALUES (?, ?)"
    for name, location in [
        ("前台电脑 A-01", "一楼前台"),
        ("财务打印机 P-03", "三楼财务部"),
        ("会议室投影仪 M-02", "二楼会议室"),
        ("研发部空调 AC-05", "四楼研发部"),
        ("办公区路由器 NET-01", "二楼机房"),
    ]:
        _conn.execute(d, (name, location))

    k = "INSERT INTO knowledge (fault_type, keywords, solution) VALUES (?, ?, ?)"
    for fault_type, keywords, solution in [
        ("电脑故障", "无法开机,蓝屏,黑屏,死机,卡顿", "重启电脑并检查电源线是否接好；开机时按 F8 进入安全模式排查；若蓝屏记录错误代码后重装对应驱动。"),
        ("电脑故障", "软件,系统,卡顿,报错", "关闭多余后台程序释放内存；卸载近期新装软件；必要时重装系统并做好数据备份。"),
        ("网络故障", "断网,连不上,网络,wifi,路由器", "检查网线是否插紧、路由器电源指示灯是否正常；重启路由器；联系网管重置 IP。"),
        ("打印机故障", "卡纸,打印,墨盒,打印机", "关闭打印机电源，打开前盖小心取出卡纸；检查墨盒/硒鼓是否耗尽；重新装纸并测试打印。"),
        ("空调故障", "不制冷,空调,漏水,温度", "清洁空调滤网；检查遥控器设置温度；若仍不制冷联系厂家补充制冷剂。"),
        ("水电故障", "漏水,跳闸,插座,灯,停电", "立即关闭对应水阀/电闸；检查线路是否过载；联系电工上门检修。"),
    ]:
        _conn.execute(k, (fault_type, keywords, solution))

    _conn.commit()
