import { afterEach, describe, expect, it, vi } from 'vitest'
import { dispatchSseChunk, streamSse } from './sse'

afterEach(() => {
  vi.unstubAllGlobals()
})

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
  return new Response(stream, { status: 200 })
}

describe('dispatchSseChunk', () => {
  it('parses named events with JSON payloads', () => {
    const onEvent = vi.fn()
    dispatchSseChunk('event: stage\ndata: {"key":"places"}', onEvent)
    expect(onEvent).toHaveBeenCalledWith('stage', { key: 'places' })
  })

  it('ignores heartbeat comments', () => {
    const onEvent = vi.fn()
    dispatchSseChunk(': ping', onEvent)
    expect(onEvent).not.toHaveBeenCalled()
  })

  it('joins multi-line data before parsing', () => {
    const onEvent = vi.fn()
    dispatchSseChunk('event: done\ndata: {"tripId":\ndata: "t1"}', onEvent)
    expect(onEvent).toHaveBeenCalledWith('done', { tripId: 't1' })
  })

  it('falls back to raw text when data is not JSON', () => {
    const onEvent = vi.fn()
    dispatchSseChunk('event: note\ndata: просто текст', onEvent)
    expect(onEvent).toHaveBeenCalledWith('note', 'просто текст')
  })

  it('defaults to the message event name', () => {
    const onEvent = vi.fn()
    dispatchSseChunk('data: 42', onEvent)
    expect(onEvent).toHaveBeenCalledWith('message', 42)
  })
})

describe('streamSse', () => {
  it('sends the event-stream accept header and emits parsed events', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      sseResponse([
        'event: stage\ndata: {"key":"analyze"}\n\n',
        ': ping\n\n',
        'event: done\ndata: {"tripId":"t1"}\n\n',
      ]),
    )
    vi.stubGlobal('fetch', fetchMock)

    const events: Array<[string, unknown]> = []
    await streamSse('/api/v1/trips/t1/stream', {
      onEvent: (name, data) => events.push([name, data]),
    })

    expect(events).toEqual([
      ['stage', { key: 'analyze' }],
      ['done', { tripId: 't1' }],
    ])

    const [, init] = fetchMock.mock.calls[0]!
    expect(new Headers(init.headers).get('Accept')).toBe('text/event-stream')
  })

  it('splits events that straddle chunk boundaries', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      sseResponse(['event: stag', 'e\ndata: {"k', 'ey":"places"}\n\n']),
    )
    vi.stubGlobal('fetch', fetchMock)

    const events: Array<[string, unknown]> = []
    await streamSse('/api/v1/x', {
      onEvent: (name, data) => events.push([name, data]),
    })

    expect(events).toEqual([['stage', { key: 'places' }]])
  })

  it('throws ApiError for non-2xx responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))
    await expect(streamSse('/api/v1/x', { onEvent: () => {} })).rejects.toMatchObject({
      status: 500,
    })
  })
})
