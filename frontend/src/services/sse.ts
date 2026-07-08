/** SSE 服务 — EventSource 连接管理 + 事件分发

  后端 SSE 路径:
  - POST /api/travel/stream  (新对话)
  - POST /api/travel/resume  (恢复 interrupt)
  - POST /api/travel/rollback (回退 checkpoint)

  因为后端 SSE 是 POST (非 GET), 不能直接用浏览器 EventSource.
  使用 fetch + ReadableStream 手动解析 SSE.
*/

import type { SSEEvent } from '@/types'

type SSEEventHandler = (event: SSEEvent) => void
type SSEErrorHandler = (error: Error) => void

/** SSE 连接管理器 */
export class SSEService {
  private controller: AbortController | null = null
  private onEvent: SSEEventHandler | null = null
  private onError: SSEErrorHandler | null = null
  private onComplete: (() => void) | null = null

  /** 注册事件处理器 */
  setHandlers(
    onEvent: SSEEventHandler,
    onError: SSEErrorHandler,
    onComplete: (() => void) | null = null,
  ) {
    this.onEvent = onEvent
    this.onError = onError
    this.onComplete = onComplete
  }

  /** POST SSE 流式请求 — 手动解析 SSE 文本流 */
  async postStream(url: string, body: Record<string, unknown>): Promise<void> {
    this.controller = new AbortController()

    // JWT 认证头
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    const token = localStorage.getItem('jwt_token')
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: this.controller.signal,
      })

      if (!response.ok) {
        let detail = response.statusText
        try {
          const errorBody = await response.json()
          detail = errorBody.detail || detail
        } catch {
          // ignore non-JSON error body
        }
        throw new Error(detail || `HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Response body is not readable')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE 协议: "data: {...}\n\n" 分隔
        const parts = buffer.split('\n\n')
        // 最后一段可能不完整, 保留在 buffer
        buffer = parts.pop() || ''

        for (const part of parts) {
          const lines = part.split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const jsonStr = line.slice(6)
              try {
                const event: SSEEvent = JSON.parse(jsonStr)
                if (this.onEvent) this.onEvent(event)
              } catch {
                // 忽略非 JSON 行
              }
            }
          }
        }
      }

      // 流结束
      if (this.onComplete) this.onComplete()
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // 用户主动断开, 不报错
        return
      }
      if (this.onError) this.onError(err instanceof Error ? err : new Error(String(err)))
    }
  }

  /** 断开 SSE 连接 */
  disconnect() {
    if (this.controller) {
      this.controller.abort()
      this.controller = null
    }
  }
}

/** 全局 SSE 实例 */
export const sseService = new SSEService()
