import { api, streamSse } from '@/shared/api'
import type {
  DoneEvent,
  GenerationErrorEvent,
  RoutePlan,
  StageEvent,
  TripCreated,
  TripDetails,
  TripDraft,
  TripSummary,
} from '../model/types'

export function createTrip(draft: TripDraft) {
  return api.post<TripCreated>('/api/v1/trips', draft, { withInitData: true })
}

export function deleteTrip(tripId: string) {
  return api.delete<void>(`/api/v1/trips/${tripId}`, { withInitData: true })
}

export function retryTrip(tripId: string) {
  return api.post<TripCreated>(`/api/v1/trips/${tripId}/retry`, undefined, {
    withInitData: true,
  })
}

export function getTrip(tripId: string) {
  return api.get<TripDetails>(`/api/v1/trips/${tripId}`, { withInitData: true })
}

export function listTrips() {
  return api.get<TripSummary[]>('/api/v1/trips', { withInitData: true })
}

export interface TripStreamHandlers {
  onStage?: (event: StageEvent) => void
  onDone?: (route: RoutePlan) => void
  onError?: (message: string) => void
}

/** Reconnect budget: 1s → 2s → 4s before the single getTrip fallback. */
const MAX_STREAM_ATTEMPTS = 3
const RECONNECT_BACKOFF_MS = [1_000, 2_000, 4_000]

function abortableDelay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal?.aborted) {
      resolve()
      return
    }
    const onAbort = () => {
      clearTimeout(timer)
      resolve()
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, ms)
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

/**
 * Follow the live generation progress of a trip.
 *
 * Resolves once the backend sends `done` or `error`. A dropped stream is
 * reconnected with backoff (stage events replay from the server, so retries
 * are idempotent). After the attempts are exhausted the trip is polled once
 * so a finished route is not lost.
 */
export async function streamTrip(
  tripId: string,
  handlers: TripStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let settled = false

  for (let attempt = 1; attempt <= MAX_STREAM_ATTEMPTS; attempt += 1) {
    if (attempt > 1) {
      await abortableDelay(RECONNECT_BACKOFF_MS[attempt - 2] ?? 4_000, signal)
    }
    if (signal?.aborted || settled) return

    try {
      await streamSse(`/api/v1/trips/${tripId}/stream`, {
        signal,
        onEvent: (name, data) => {
          if (name === 'stage') {
            handlers.onStage?.(data as StageEvent)
            return
          }
          if (name === 'done') {
            settled = true
            handlers.onDone?.((data as DoneEvent).route)
            return
          }
          if (name === 'error') {
            settled = true
            handlers.onError?.((data as GenerationErrorEvent).message)
          }
        },
      })
    } catch {
      if (signal?.aborted || settled) return
      // Drop or HTTP error — the loop retries, then falls back to getTrip.
      continue
    }

    if (settled || signal?.aborted) return
    // Clean close without a verdict — the trip may still be running.
  }

  if (settled || signal?.aborted) return

  // Every attempt dropped without a verdict — fall back to the stored trip.
  const trip = await getTrip(tripId)
  if (trip.status === 'ready' && trip.route) {
    handlers.onDone?.(trip.route)
  } else if (trip.status === 'failed') {
    handlers.onError?.(trip.error ?? 'Не удалось построить маршрут')
  } else {
    handlers.onError?.('Соединение прервалось. Попробуйте ещё раз.')
  }
}
