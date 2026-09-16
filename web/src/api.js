// api.js —— 统一请求封装：自动携带 token、统一处理 401/错误
// token 支持两种来源：
//   1. 显式传入（三端演示面板各自持有独立 token，互不影响）
//   2. 未传时回退到 localStorage（普通单用户模式，保留原有登录态失效跳转逻辑）
export async function request(path, { method = 'GET', body, token } = {}) {
  const fromLocal = token === undefined
  const t = fromLocal ? localStorage.getItem('token') : (token || '')
  const headers = {}
  if (t) headers.Authorization = 'Bearer ' + t

  const res = await fetch('/api' + path, {
    method,
    headers: body ? { ...headers, 'Content-Type': 'application/json' } : headers,
    body: body ? JSON.stringify(body) : undefined
  })

  if (!res.ok) {
    let msg = '请求失败 ' + res.status
    try { msg = (await res.json()).error || msg } catch (e) {}

    // 只有“曾携带 token 却仍被 401”才视为登录态失效并跳登录页；
    // 登录接口自身的 401（账号或密码错误）应原样展示真实错误信息
    if (res.status === 401 && t && fromLocal) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (location.hash !== '#/login') location.hash = '#/login'
    }
    throw new Error(msg)
  }
  return res.json()
}
