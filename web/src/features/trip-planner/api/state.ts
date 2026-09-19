import { api } from '@/shared/api'
import type { LedgerEntry, LedgerKind, PackingBlock } from '../model/useTripLocalState'

interface TripStatePayload {
  packing: PackingBlock[]
}

export function getTripState(tripId: string) {
  return api.get<TripStatePayload>(`/api/v1/trips/${tripId}/state`, {
    withInitData: true,
  })
}

export function saveTripState(tripId: string, packing: PackingBlock[]) {
  return api.put<TripStatePayload>(
    `/api/v1/trips/${tripId}/state`,
    { packing },
    { withInitData: true },
  )
}

export function listLedger(tripId: string) {
  return api.get<LedgerEntry[]>(`/api/v1/trips/${tripId}/ledger`, {
    withInitData: true,
  })
}

export interface LedgerInput {
  kind: LedgerKind
  amount: number
  title: string
  date?: string
}

export function createLedgerEntry(tripId: string, input: LedgerInput) {
  return api.post<LedgerEntry>(`/api/v1/trips/${tripId}/ledger`, input, {
    withInitData: true,
  })
}

export function deleteLedgerEntry(tripId: string, entryId: string) {
  return api.delete<void>(`/api/v1/trips/${tripId}/ledger/${entryId}`, {
    withInitData: true,
  })
}
