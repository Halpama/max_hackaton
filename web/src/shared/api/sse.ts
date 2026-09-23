import { API_BASE_URL } from '@/shared/config'
import { getInitData } from '@/shared/lib/max'
import { ApiError } from '@/shared/utils'

export interface SseHandlers {
  /** Called for every named event with its parsed JSON payload. */
  onEvent: (event: string, data: unknown) => void
  signal?: AbortSignal
}

/**
 * Read a Server-Sent Events stream over `fetch`.
 *
 * The native `EventSource` cannot set request headers, and the backend expects
 * MAX `initData` in `Authorization`, so we parse the stream by hand.
 */
export async function streamSse(path: string, { onEvent, signal }: SseHandlers): Promise<void> {
  const headers = new Headers({ Accept: 'text/event-stream' })
  const initData = getInitData()
  if (initData) {
    headers.set('Authorization', `tma ${initData}`)
  }

  const normalized = path.startsWith('/') ? path : `/${path}`
  const response = await fetch(`${API_BASE_URL}${normalized}`, {
    headers,
    signal,
  })

  if (!response.ok || !response.body) {
    throw new ApiError(
      `Stream failed: ${response.status} ${response.statusText}`,
      response.status,
    )
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Events are separated by a blank line.
      let separator = buffer.indexOf('\n\n')
      while (separator !== -1) {
        dispatchSseChunk(buffer.slice(0, separator), onEvent)
        buffer = buffer.slice(separator + 2)
        separator = buffer.indexOf('\n\n')
      }
    }
  } finally {
    reader.cancel().catch(() => {})
  }
}

/** Parse one SSE chunk (`event:` / `data:` lines) and emit it. Exported for tests. */
export function dispatchSseChunk(chunk: string, onEvent: SseHandlers['onEvent']) {
  let eventName = 'message'
  const dataLines: string[] = []

  for (const line of chunk.split('\n')) {
    // Lines starting with ':' are comments — the backend uses them as heartbeats.
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }

  if (dataLines.length === 0) return

  try {
    onEvent(eventName, JSON.parse(dataLines.join('\n')))
  } catch {
    onEvent(eventName, dataLines.join('\n'))
  }
}
