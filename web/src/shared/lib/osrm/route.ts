import { withOsrmCache } from './cache'
import type { LngLat, RouteProfile, TransitModeLike } from './types'

export type { LngLat, RouteProfile, TransitModeLike }

interface OsrmRouteResponse {
  code?: string
  routes?: Array<{
    geometry?: {
      coordinates?: number[][]
    }
  }>
}

const ENDPOINTS: Record<RouteProfile, readonly string[]> = {
  foot: [
    'https://routing.openstreetmap.de/routed-foot/route/v1/foot',
    'https://router.project-osrm.org/route/v1/foot',
  ],
  driving: [
    'https://routing.openstreetmap.de/routed-car/route/v1/driving',
    'https://router.project-osrm.org/route/v1/driving',
  ],
}

/** Map backend transit mode → OSRM profile */
export function profileFromTransitMode(
  mode: TransitModeLike | null | undefined,
): RouteProfile {
  if (mode === 'taxi') return 'driving'
  // walk / metro / unknown → pedestrian network
  return 'foot'
}

async function fetchProfileRouteNetwork(
  coords: LngLat[],
  profile: RouteProfile,
  signal?: AbortSignal,
): Promise<LngLat[]> {
  const path = coords.map(([lng, lat]) => `${lng},${lat}`).join(';')
  const query = '?overview=full&geometries=geojson'
  let lastError: unknown

  for (const base of ENDPOINTS[profile]) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')

    try {
      const response = await fetch(`${base}/${path}${query}`, { signal })
      if (!response.ok) {
        lastError = new Error(`OSRM HTTP ${response.status}`)
        continue
      }

      const data = (await response.json()) as OsrmRouteResponse
      const geometry = data.routes?.[0]?.geometry?.coordinates
      if (!geometry?.length) {
        lastError = new Error('OSRM returned empty geometry')
        continue
      }

      return geometry.map(([lng, lat]) => [lng, lat] as LngLat)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      lastError = error
    }
  }

  throw lastError instanceof Error ? lastError : new Error('OSRM unavailable')
}

async function fetchProfileRoute(
  coords: LngLat[],
  profile: RouteProfile,
  signal?: AbortSignal,
): Promise<LngLat[]> {
  if (coords.length < 2) return coords

  // Cache per A→B (+ profile). Day routes are stitched from these legs so
  // switching days / revisiting a trip hits localStorage instead of OSRM.
  // Network fetch is not aborted by the caller signal so a shared in-flight
  // request can still fill the cache; the caller stops waiting via withOsrmCache.
  return withOsrmCache(
    coords,
    profile,
    () => fetchProfileRouteNetwork(coords, profile),
    signal,
  )
}

/**
 * Build a day polyline from place coords + per-leg transit modes from backend.
 * Each segment is routed with foot or driving according to that leg's mode.
 */
export async function fetchRoadRoute(
  coords: LngLat[],
  legModes: Array<TransitModeLike | null | undefined> = [],
  signal?: AbortSignal,
): Promise<LngLat[]> {
  if (coords.length < 2) return coords

  // Single shared mode for the whole path (legacy / short calls)
  if (coords.length === 2) {
    return fetchProfileRoute(
      coords,
      profileFromTransitMode(legModes[0]),
      signal,
    )
  }

  const merged: LngLat[] = []

  for (let i = 0; i < coords.length - 1; i += 1) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')

    const profile = profileFromTransitMode(legModes[i])
    const segment = await fetchProfileRoute(
      [coords[i], coords[i + 1]],
      profile,
      signal,
    )

    if (merged.length === 0) {
      merged.push(...segment)
    } else {
      merged.push(...segment.slice(1))
    }
  }

  return merged.length > 0 ? merged : coords
}
