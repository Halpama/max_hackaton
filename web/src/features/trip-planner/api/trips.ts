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

/**
 * Follow the live generation progress of a trip.
 *
 * Resolves once the backend sends `done` or `error`. If the stream drops before
 * either arrives, the trip is polled once so a finished route is not lost.
 */
export async function streamTrip(
  tripId: string,
  handlers: TripStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let settled = false

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
  } catch (error) {
    if (signal?.aborted) return
    throw error
  }

  if (settled || signal?.aborted) return

  // Stream closed without a verdict — fall back to the stored trip.
  const trip = await getTrip(tripId)
  if (trip.status === 'ready' && trip.route) {
    handlers.onDone?.(trip.route)
  } else if (trip.status === 'failed') {
    handlers.onError?.(trip.error ?? 'Не удалось построить маршрут')
  } else {
    handlers.onError?.('Соединение прервалось. Попробуйте ещё раз.')
  }
}
