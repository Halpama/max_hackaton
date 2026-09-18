import { useCallback, useEffect, useMemo, useState } from 'react'

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
  return raw.flatMap((item) => {
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
}

function readState(tripId: string): TripLocalState {
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

export function useTripLocalState(tripId: string, plannedBudget: number) {
  const [packing, setPacking] = useState<PackingBlock[]>(() => readState(tripId).packing)
  const [ledger, setLedger] = useState<LedgerEntry[]>(() => readState(tripId).ledger)

  useEffect(() => {
    const next = readState(tripId)
    setPacking(next.packing)
    setLedger(next.ledger)
  }, [tripId])

  useEffect(() => {
    localStorage.setItem(storageKey(tripId), JSON.stringify({ packing, ledger }))
  }, [tripId, packing, ledger])

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
      setLedger((prev) => [
        {
          id: createId(),
          kind: input.kind,
          amount,
          title: input.title.trim() || (input.kind === 'expense' ? 'Трата' : 'Пополнение'),
          date: input.date || todayIso(),
          createdAt: Date.now(),
        },
        ...prev,
      ])
    },
    [],
  )

  const removeLedgerEntry = useCallback((id: string) => {
    setLedger((prev) => prev.filter((e) => e.id !== id))
  }, [])

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
