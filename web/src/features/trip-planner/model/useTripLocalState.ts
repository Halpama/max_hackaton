import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { USE_MOCKS } from '@/shared/config'
import {
  createLedgerEntry,
  deleteLedgerEntry,
  getTripState,
  listLedger,
  saveTripState,
} from '../api'

export type PackingBlock =
  | { id: string; type: 'text'; text: string }
  | { id: string; type: 'bullet'; text: string }
  | { id: string; type: 'check'; text: string; done: boolean }

export type LedgerKind = 'expense' | 'topup'

export interface LedgerEntry {
  id: string
  kind: LedgerKind
  amount: number
  title: string
  /** YYYY-MM-DD */
  date: string
  createdAt: number
}

interface TripLocalState {
  packing: PackingBlock[]
  ledger: LedgerEntry[]
}

const STORAGE_PREFIX = 'tp-trip-local:'
/** Packing is a live editor — batch keystrokes before hitting the API. */
const SAVE_DEBOUNCE_MS = 700

function storageKey(tripId: string) {
  return `${STORAGE_PREFIX}${tripId}`
}

function createId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

function todayIso() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function defaultPacking(): PackingBlock[] {
  return [{ id: createId(), type: 'text', text: '' }]
}

function normalizePacking(raw: unknown): PackingBlock[] {
  if (!Array.isArray(raw) || raw.length === 0) return defaultPacking()
  const blocks = raw.flatMap<PackingBlock>((item) => {
    if (!item || typeof item !== 'object') return []
    const block = item as Partial<PackingBlock> & { id?: string; text?: string }
    if (!block.id || typeof block.text !== 'string') return []
    if (block.type === 'check') {
      return [{ id: block.id, type: 'check', text: block.text, done: Boolean((block as { done?: boolean }).done) }]
    }
    if (block.type === 'bullet') {
      return [{ id: block.id, type: 'bullet', text: block.text }]
    }
    return [{ id: block.id, type: 'text', text: block.text }]
  })

  return blocks.length > 0 ? blocks : defaultPacking()
}

function readLocal(tripId: string): TripLocalState {
  try {
    const raw = localStorage.getItem(storageKey(tripId))
    if (!raw) return { packing: defaultPacking(), ledger: [] }
    const parsed = JSON.parse(raw) as Partial<TripLocalState>
    return {
      packing: normalizePacking(parsed.packing),
      ledger: Array.isArray(parsed.ledger) ? parsed.ledger : [],
    }
  } catch {
    return { packing: defaultPacking(), ledger: [] }
  }
}

function writeLocal(tripId: string, state: TripLocalState) {
  try {
    localStorage.setItem(storageKey(tripId), JSON.stringify(state))
  } catch {
    // Storage full or blocked — nothing we can do here.
  }
}

/**
 * Packing checklist and budget ledger for one trip.
 *
 * Backed by the API when a real trip is open; falls back to localStorage in mock
 * mode or before a trip exists, so the panels always have somewhere to write.
 */
export function useTripLocalState(tripId: string, plannedBudget: number) {
  const offline = USE_MOCKS || !tripId

  const [packing, setPacking] = useState<PackingBlock[]>(() =>
    offline ? readLocal(tripId).packing : defaultPacking(),
  )
  const [ledger, setLedger] = useState<LedgerEntry[]>(() =>
    offline ? readLocal(tripId).ledger : [],
  )

  const saveTimerRef = useRef<number | undefined>(undefined)
  // Skip the save that would otherwise fire right after loading from the server.
  const hydratedRef = useRef(false)

  useEffect(() => {
    hydratedRef.current = false

    if (offline) {
      const local = readLocal(tripId)
      setPacking(local.packing)
      setLedger(local.ledger)
      hydratedRef.current = true
      return
    }

    let cancelled = false

    const load = async () => {
      try {
        const [state, entries] = await Promise.all([
          getTripState(tripId),
          listLedger(tripId),
        ])
        if (cancelled) return
        setPacking(normalizePacking(state.packing))
        setLedger(entries)
      } catch {
        if (!cancelled) {
          // Offline or the trip is gone — keep the local copy as a draft.
          const local = readLocal(tripId)
          setPacking(local.packing)
          setLedger(local.ledger)
        }
      } finally {
        if (!cancelled) hydratedRef.current = true
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [tripId, offline])

  // Persist packing: localStorage always (as a cache), API on a debounce.
  useEffect(() => {
    if (!hydratedRef.current) return

    writeLocal(tripId, { packing, ledger })
    if (offline) return

    window.clearTimeout(saveTimerRef.current)
    saveTimerRef.current = window.setTimeout(() => {
      saveTripState(tripId, packing).catch(() => {})
    }, SAVE_DEBOUNCE_MS)

    return () => window.clearTimeout(saveTimerRef.current)
  }, [tripId, packing, ledger, offline])

  const spent = useMemo(
    () => ledger.filter((e) => e.kind === 'expense').reduce((sum, e) => sum + e.amount, 0),
    [ledger],
  )
  const toppedUp = useMemo(
    () => ledger.filter((e) => e.kind === 'topup').reduce((sum, e) => sum + e.amount, 0),
    [ledger],
  )
  const remaining = plannedBudget + toppedUp - spent

  const addLedgerEntry = useCallback(
    (input: { kind: LedgerKind; amount: number; title: string; date?: string }) => {
      const amount = Math.max(1, Math.floor(input.amount))
      const title = input.title.trim() || (input.kind === 'expense' ? 'Трата' : 'Пополнение')
      const date = input.date || todayIso()
      const optimistic: LedgerEntry = {
        id: createId(),
        kind: input.kind,
        amount,
        title,
        date,
        createdAt: Date.now(),
      }

      setLedger((prev) => [optimistic, ...prev])
      if (offline) return

      createLedgerEntry(tripId, { kind: input.kind, amount, title, date })
        .then((saved) => {
          // Swap the temporary id for the server one.
          setLedger((prev) => prev.map((e) => (e.id === optimistic.id ? saved : e)))
        })
        .catch(() => {
          setLedger((prev) => prev.filter((e) => e.id !== optimistic.id))
        })
    },
    [tripId, offline],
  )

  const removeLedgerEntry = useCallback(
    (id: string) => {
      const removed = ledger.find((e) => e.id === id)
      setLedger((prev) => prev.filter((e) => e.id !== id))
      if (offline || !removed) return

      deleteLedgerEntry(tripId, id).catch(() => {
        setLedger((prev) => [removed, ...prev])
      })
    },
    [ledger, tripId, offline],
  )

  const updatePacking = useCallback((next: PackingBlock[]) => {
    setPacking(next)
  }, [])

  return {
    packing,
    updatePacking,
    ledger,
    addLedgerEntry,
    removeLedgerEntry,
    plannedBudget,
    spent,
    toppedUp,
    remaining,
    createId,
    todayIso,
  }
}

export function groupLedgerByDate(entries: LedgerEntry[]) {
  const map = new Map<string, LedgerEntry[]>()
  for (const entry of entries) {
    const list = map.get(entry.date) ?? []
    list.push(entry)
    map.set(entry.date, list)
  }

  return [...map.entries()]
    .sort(([a], [b]) => (a < b ? 1 : a > b ? -1 : 0))
    .map(([date, items]) => ({
      date,
      items: items.sort((a, b) => b.createdAt - a.createdAt),
    }))
}

export function formatDayHeading(iso: string) {
  const date = new Date(`${iso}T12:00:00`)
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
}

export function formatMoney(value: number) {
  return Math.round(value).toLocaleString('ru-RU')
}
