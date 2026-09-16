# errors.py —— 业务错误：保持前端 api.js 读取的 {error: '提示'} 契约
# 对应 Express 版 res.status(4xx).json({ error: '提示' })


class ApiError(Exception):
    """业务异常：status_code 对应 HTTP 状态码，message 是给前端的中文提示。"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)
