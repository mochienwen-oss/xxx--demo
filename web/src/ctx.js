// ctx.js —— 请求上下文：三端演示面板传 session，普通单用户走全局 auth
import { auth } from './store'

export function makeCtx(session) {
  return {
    // 普通模式返回 undefined，让 api.request 回退到 localStorage（保留原 401 处理）
    get token() { return session ? session.token : undefined },
    get user() { return session ? session.user : auth.user }
  }
}
