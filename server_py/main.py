# main.py —— FastAPI 后端入口（对应 Express 版 server.js）
# 接口契约与 JS 版完全一致：URL 前缀、HTTP 方法、JSON 字段、{error} 提示、Bearer token。
# 启动（保持端口 3000，前端 vite 代理无需改动）：
#   cd server_py
#   pip install -r requirements.txt
#   python main.py          # 或 uvicorn main:app --port 3000
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from errors import ApiError
from routers import auth as auth_router
from routers import meta as meta_router
from routers import smart as smart_router
from routers import tickets as tickets_router

app = FastAPI(title="xxx公司智能报修系统 后端 API", version="2.0.0")


# 统一错误契约：任何 ApiError 都返回 {error: '提示'}，等价 Express 的 res.status(4xx).json({error})
@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


# 参数校验失败（Pydantic）也走 {error} 契约，避免前端读到 FastAPI 默认的 detail 字段
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "请求参数不合法"})


# 路由挂载（对应 server.js 的 4 行 app.use）
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(tickets_router.router, prefix="/api/tickets", tags=["tickets"])
app.include_router(smart_router.router, prefix="/api/smart", tags=["smart"])
app.include_router(meta_router.router, prefix="/api", tags=["meta"])


# 未知 /api 路径兜底：保持 {error} 契约
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def api_not_found(path: str):
    raise ApiError(404, "接口不存在")


# 生产模式：若前端已构建（web/dist 存在），则托管静态文件（对应 server.js 的 express.static）
dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")
if os.path.isdir(dist):
    app.mount("/", StaticFiles(directory=dist, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=3000)
