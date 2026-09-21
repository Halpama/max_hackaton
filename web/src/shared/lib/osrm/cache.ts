import type { LngLat, RouteProfile } from './types'

/**
 * localStorage cache for OSRM leg geometries.
 *
 * Key design (avoids common bugs):
 * - version prefix → bump to invalidate all entries after format changes
 * - profile in the key → foot ≠ driving for the same pair
 * - coords rounded to fixed decimals → "37.6173" vs "37.6173000001" don't miss
 * - only A→B segments are stored (day polylines are composed of legs)
 * - entries carry TTL; expired / corrupt rows are dropped on read
 * - in-flight map dedupes concurrent identical requests
 */

const CACHE_VERSION = 1
const CACHE_PREFIX = `tp:osrm:v${CACHE_VERSION}:`
/** ~1.1 m — enough to reuse, not enough to glue distinct places together */
const COORD_DECIMALS = 5
const TTL_MS = 14 * 24 * 60 * 60 * 1000
const MAX_ENTRIES = 100

type CacheRecord = {
  v: typeof CACHE_VERSION
  /** unix ms expiry */
  exp: number
  geom: LngLat[]
}

const memory = new Map<string, CacheRecord>()
const inflight = new Map<string, Promise<LngLat[]>>()

function storageAvailable(): boolean {
  try {
    if (typeof localStorage === 'undefined') return false
    const probe = '__tp_osrm_probe__'
    localStorage.setItem(probe, '1')
    localStorage.removeItem(probe)
    return true
  } catch {
    return false
  }
}

const canUseStorage = storageAvailable()

/** Stable string for a float — no "-0", no scientific notation surprises. */
function roundCoord(value: number): string {
  if (!Number.isFinite(value)) return 'NaN'
  const rounded = Number(value.toFixed(COORD_DECIMALS))
  return (Object.is(rounded, -0) ? 0 : rounded).toFixed(COORD_DECIMALS)
}

export function osrmCacheKey(coords: LngLat[], profile: RouteProfile): string {
  const path = coords.map(([lng, lat]) => `${roundCoord(lng)},${roundCoord(lat)}`).join(';')
  return `${CACHE_PREFIX}${profile}:${path}`
}

function isLngLat(value: unknown): value is LngLat {
  return (
    Array.isArray(value) &&
    value.length === 2 &&
    typeof value[0] === 'number' &&
    typeof value[1] === 'number' &&
    Number.isFinite(value[0]) &&
    Number.isFinite(value[1])
  )
}

function parseRecord(raw: string): CacheRecord | null {
  try {
    const data = JSON.parse(raw) as Partial<CacheRecord>
    if (data.v !== CACHE_VERSION) return null
    if (typeof data.exp !== 'number' || !Number.isFinite(data.exp)) return null
    if (!Array.isArray(data.geom) || data.geom.length < 2) return null
    if (!data.geom.every(isLngLat)) return null
    return { v: CACHE_VERSION, exp: data.exp, geom: data.geom }
  } catch {
    return null
  }
}

function readStorage(key: string): CacheRecord | null {
  if (!canUseStorage) return null
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const record = parseRecord(raw)
    if (!record) {
      localStorage.removeItem(key)
      return null
    }
    if (record.exp <= Date.now()) {
      localStorage.removeItem(key)
      memory.delete(key)
      return null
    }
    return record
  } catch {
    return null
  }
}

function listCacheKeys(): string[] {
  if (!canUseStorage) return []
  const keys: string[] = []
  try {
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i)
      if (key?.startsWith(CACHE_PREFIX)) keys.push(key)
    }
  } catch {
    return keys
  }
  return keys
}

function evictIfNeeded(): void {
  if (!canUseStorage) return
  const keys = listCacheKeys()
  if (keys.length < MAX_ENTRIES) return

  const ranked = keys
    .map((key) => {
      const raw = localStorage.getItem(key)
      const record = raw ? parseRecord(raw) : null
      return { key, exp: record?.exp ?? 0 }
    })
    .sort((a, b) => a.exp - b.exp)

  const overflow = keys.length - MAX_ENTRIES + 1
  for (let i = 0; i < overflow; i += 1) {
    const victim = ranked[i]
    if (!victim) break
    try {
      localStorage.removeItem(victim.key)
    } catch {
      // ignore
    }
    memory.delete(victim.key)
  }
}

function writeStorage(key: string, record: CacheRecord): void {
  memory.set(key, record)
  if (!canUseStorage) return

  const payload = JSON.stringify(record)
  const attempt = () => {
    localStorage.setItem(key, payload)
  }

  try {
    evictIfNeeded()
    attempt()
  } catch {
    try {
      const keys = listCacheKeys()
        .map((k) => {
          const raw = localStorage.getItem(k)
          const parsed = raw ? parseRecord(raw) : null
          return { key: k, exp: parsed?.exp ?? 0 }
        })
        .sort((a, b) => a.exp - b.exp)

      const drop = Math.max(8, Math.ceil(keys.length / 2))
      for (let i = 0; i < drop; i += 1) {
        const victim = keys[i]
        if (!victim) break
        localStorage.removeItem(victim.key)
        memory.delete(victim.key)
      }
      attempt()
    } catch {
      // routing still works without cache
    }
  }
}

export function readOsrmCache(coords: LngLat[], profile: RouteProfile): LngLat[] | null {
  const key = osrmCacheKey(coords, profile)
  const mem = memory.get(key)
  if (mem) {
    if (mem.exp <= Date.now()) {
      memory.delete(key)
    } else {
      return mem.geom
    }
  }

  const stored = readStorage(key)
  if (!stored) return null
  memory.set(key, stored)
  return stored.geom
}

export function writeOsrmCache(
  coords: LngLat[],
  profile: RouteProfile,
  geom: LngLat[],
): void {
  if (geom.length < 2) return
  if (!geom.every(isLngLat)) return

  const key = osrmCacheKey(coords, profile)
  writeStorage(key, {
    v: CACHE_VERSION,
    exp: Date.now() + TTL_MS,
    geom,
  })
}

/**
 * Run `loader` once per cache key; concurrent callers share the same promise.
 * Successful results are written to localStorage; abort/errors are not cached.
 * Caller's AbortSignal only cancels *waiting* — an in-flight shared fetch may
 * still finish and fill the cache (good for fast day switching).
 */
export function withOsrmCache(
  coords: LngLat[],
  profile: RouteProfile,
  loader: () => Promise<LngLat[]>,
  signal?: AbortSignal,
): Promise<LngLat[]> {
  if (signal?.aborted) {
    return Promise.reject(new DOMException('Aborted', 'AbortError'))
  }

  const cached = readOsrmCache(coords, profile)
  if (cached) return Promise.resolve(cached)

  const key = osrmCacheKey(coords, profile)
  let pending = inflight.get(key)
  if (!pending) {
    pending = loader()
      .then((geom) => {
        writeOsrmCache(coords, profile, geom)
        return geom
      })
      .finally(() => {
        inflight.delete(key)
      })
    inflight.set(key, pending)
  }

  if (!signal) return pending

  return new Promise<LngLat[]>((resolve, reject) => {
    const onAbort = () => {
      reject(new DOMException('Aborted', 'AbortError'))
    }
    signal.addEventListener('abort', onAbort, { once: true })
    pending!.then(
      (value) => {
        signal.removeEventListener('abort', onAbort)
        if (signal.aborted) {
          reject(new DOMException('Aborted', 'AbortError'))
          return
        }
        resolve(value)
      },
      (error) => {
        signal.removeEventListener('abort', onAbort)
        reject(error)
      },
    )
  })
}
