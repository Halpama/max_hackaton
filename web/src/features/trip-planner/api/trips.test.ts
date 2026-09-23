import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, streamSse } from '@/shared/api'
import { streamTrip } from './trips'

vi.mock('@/shared/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  streamSse: vi.fn(),
}))

type StreamArgs = Parameters<typeof streamSse>[1]

const ROUTE = { city: 'Санкт-Петербург', days: [], places: {} } as never

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
})

describe('streamTrip reconnect', () => {
  it('retries a dropped stream and resolves on done', async () => {
    vi.mocked(streamSse)
      .mockRejectedValueOnce(new Error('network down'))
      .mockImplementationOnce(async (_path, handlers: StreamArgs) => {
        handlers.onEvent('stage', { key: 'places' })
        handlers.onEvent('done', { tripId: 't1', route: ROUTE })
      })

    const onDone = vi.fn()
    const promise = streamTrip('t1', { onDone })

    await vi.advanceTimersByTimeAsync(1_000)
    await promise

    expect(streamSse).toHaveBeenCalledTimes(2)
    expect(onDone).toHaveBeenCalledWith(ROUTE)
    expect(api.get).not.toHaveBeenCalled()
  })

  it('falls back to getTrip after every attempt drops', async () => {
    vi.mocked(streamSse).mockRejectedValue(new Error('down'))
    vi.mocked(api.get).mockResolvedValue({
      status: 'failed',
      error: 'Не удалось построить маршрут',
    })

    const onError = vi.fn()
    const promise = streamTrip('t1', { onError })

    await vi.advanceTimersByTimeAsync(1_000)
    await vi.advanceTimersByTimeAsync(2_000)
    await promise

    expect(streamSse).toHaveBeenCalledTimes(3)
    expect(api.get).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith('Не удалось построить маршрут')
  })

  it('does not reconnect after an abort', async () => {
    const controller = new AbortController()
    vi.mocked(streamSse).mockImplementation(async () => {
      controller.abort()
      throw new Error('aborted')
    })

    await streamTrip('t1', {}, controller.signal)

    expect(streamSse).toHaveBeenCalledTimes(1)
    expect(api.get).not.toHaveBeenCalled()
  })

  it('stops retrying once done has settled', async () => {
    vi.mocked(streamSse).mockImplementation(async (_path, handlers: StreamArgs) => {
      handlers.onEvent('done', { tripId: 't1', route: ROUTE })
      // Stream keeps going after done — must not trigger another attempt.
      throw new Error('dropped after done')
    })

    const onDone = vi.fn()
    await streamTrip('t1', { onDone })

    expect(onDone).toHaveBeenCalledTimes(1)
    expect(streamSse).toHaveBeenCalledTimes(1)
  })

  it('uses a one-shot getTrip when the stream closes cleanly without a verdict', async () => {
    vi.mocked(streamSse)
      .mockResolvedValueOnce(undefined) // clean close, no done/error
      .mockRejectedValueOnce(new Error('down'))
      .mockRejectedValueOnce(new Error('down'))
    vi.mocked(api.get).mockResolvedValue({ status: 'pending' })

    const onError = vi.fn()
    const promise = streamTrip('t1', { onError })

    await vi.advanceTimersByTimeAsync(1_000)
    await vi.advanceTimersByTimeAsync(2_000)
    await promise

    expect(api.get).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith('Соединение прервалось. Попробуйте ещё раз.')
  })
})
