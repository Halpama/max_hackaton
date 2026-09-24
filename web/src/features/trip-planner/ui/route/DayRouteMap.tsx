import { useEffect, useRef, useState } from 'react'
import { YANDEX_MAPS_TILES_KEY } from '@/shared/config'
import {
  ensureMapLibreWorker,
  LngLatBounds,
  Map,
  Marker,
  type MaplibreMap,
  type MaplibreMarker,
} from '@/shared/lib/maplibre'
import { fetchRoadRoute, type LngLat, type TransitModeLike } from '@/shared/lib/osrm'
import type { Place } from '../../model'
import styles from './DayRouteMap.module.css'

interface DayRouteMapProps {
  places: Place[]
  /** Per-leg transit modes from backend between consecutive places */
  legModes?: Array<TransitModeLike | null | undefined>
}

type MapStatus = 'loading' | 'ready' | 'error'
type RenderPlaces = (
  dayPlaces: Place[],
  modes: Array<TransitModeLike | null | undefined>,
) => void

const DEFAULT_CENTER: LngLat = [30.31456, 59.93984]
const CAMERA_DURATION_MS = 850
const ROUTE_DRAW_MS = 950

function buildBasemapStyle() {
  const sourceId = 'basemap'
  const tiles = YANDEX_MAPS_TILES_KEY
    ? [
        `https://tiles.api-maps.yandex.ru/v1/tiles/?${new URLSearchParams({
          apikey: YANDEX_MAPS_TILES_KEY,
          lang: 'ru_RU',
          l: 'map',
          projection: 'web_mercator',
        }).toString()}&x={x}&y={y}&z={z}`,
      ]
    : ['https://tile.openstreetmap.org/{z}/{x}/{y}.png']
  const attribution = YANDEX_MAPS_TILES_KEY ? '© Яндекс Карты' : '&copy; OpenStreetMap'

  return {
    version: 8 as const,
    sources: {
      [sourceId]: {
        type: 'raster' as const,
        tiles,
        tileSize: 256,
        attribution,
        maxzoom: 19,
      },
    },
    layers: [
      {
        id: sourceId,
        type: 'raster' as const,
        source: sourceId,
      },
    ],
  }
}

const BASEMAP_STYLE = buildBasemapStyle()

function pointsLabel(count: number) {
  if (count === 1) return 'точка'
  if (count >= 2 && count <= 4) return 'точки'
  return 'точек'
}

function createPin(n: number) {
  const el = document.createElement('div')
  el.className = styles.pin
  el.textContent = String(n)
  return el
}

function createRouteOverlay() {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svg.setAttribute('class', styles.routeSvg)
  svg.setAttribute('aria-hidden', 'true')

  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
  path.setAttribute('class', styles.routeLine)
  svg.appendChild(path)

  return { svg, path }
}

function forceMapLayout(map: MaplibreMap) {
  try {
    map.resize()
  } catch {
    // map may already be removed
  }
}

function projectPath(map: MaplibreMap, coords: LngLat[]) {
  if (coords.length < 2) return ''
  return coords
    .map((coord, index) => {
      const point = map.project(coord)
      return `${index === 0 ? 'M' : 'L'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`
    })
    .join(' ')
}

function easeOutCubic(t: number) {
  return 1 - (1 - t) ** 3
}

function sliceRouteProgress(coords: LngLat[], progress: number): LngLat[] {
  if (coords.length < 2) return coords
  const t = Math.min(1, Math.max(0, progress))
  if (t <= 0) return [coords[0]]
  if (t >= 1) return coords

  const segments = coords.length - 1
  const exact = t * segments
  const index = Math.floor(exact)
  const local = exact - index
  const from = coords[index]
  const to = coords[Math.min(index + 1, coords.length - 1)]
  const interpolated: LngLat = [
    from[0] + (to[0] - from[0]) * local,
    from[1] + (to[1] - from[1]) * local,
  ]
  return [...coords.slice(0, index + 1), interpolated]
}

function waitForSize(el: HTMLElement, signal: AbortSignal): Promise<void> {
  if (el.clientWidth > 0 && el.clientHeight > 0) return Promise.resolve()

  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }

    const done = () => {
      observer.disconnect()
      signal.removeEventListener('abort', onAbort)
      resolve()
    }

    const onAbort = () => {
      observer.disconnect()
      reject(new DOMException('Aborted', 'AbortError'))
    }

    const observer = new ResizeObserver(() => {
      if (el.clientWidth > 0 && el.clientHeight > 0) done()
    })

    observer.observe(el)
    signal.addEventListener('abort', onAbort, { once: true })

    window.setTimeout(() => {
      if (!signal.aborted) done()
    }, 800)
  })
}

export function DayRouteMap({ places, legModes = [] }: DayRouteMapProps) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MaplibreMap | null>(null)
  const markersRef = useRef<MaplibreMarker[]>([])
  const routeCoordsRef = useRef<LngLat[]>([])
  const routePathRef = useRef<SVGPathElement | null>(null)
  const renderPlacesRef = useRef<RenderPlaces | null>(null)
  const placesRef = useRef(places)
  const legModesRef = useRef(legModes)
  const routeAbortRef = useRef<AbortController | null>(null)
  const routeAnimRef = useRef(0)
  const [status, setStatus] = useState<MapStatus>('loading')

  useEffect(() => {
    placesRef.current = places
  }, [places])

  useEffect(() => {
    legModesRef.current = legModes
  }, [legModes])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const abort = new AbortController()
    let cancelled = false
    let markedReady = false
    const timers: number[] = []
    let pollId = 0
    const cleanupFns: Array<() => void> = []

    const redrawPath = () => {
      const map = mapRef.current
      const path = routePathRef.current
      if (!map || !path) return
      path.setAttribute('d', projectPath(map, routeCoordsRef.current))
    }

    const stopRouteAnimation = () => {
      if (routeAnimRef.current) {
        cancelAnimationFrame(routeAnimRef.current)
        routeAnimRef.current = 0
      }
    }

    const setRouteCoords = (coords: LngLat[]) => {
      stopRouteAnimation()
      routeCoordsRef.current = coords
      redrawPath()
    }

    const animateRouteDraw = (coords: LngLat[]) => {
      stopRouteAnimation()
      if (coords.length < 2) {
        routeCoordsRef.current = coords
        redrawPath()
        return
      }

      routeCoordsRef.current = [coords[0]]
      redrawPath()
      const started = performance.now()

      const tick = (now: number) => {
        if (cancelled) return
        const progress = easeOutCubic(Math.min(1, (now - started) / ROUTE_DRAW_MS))
        routeCoordsRef.current = sliceRouteProgress(coords, progress)
        redrawPath()
        if (progress < 1) {
          routeAnimRef.current = requestAnimationFrame(tick)
        } else {
          routeAnimRef.current = 0
          routeCoordsRef.current = coords
          redrawPath()
        }
      }

      routeAnimRef.current = requestAnimationFrame(tick)
    }

    const fitPlaces = (map: MaplibreMap, coords: LngLat[], animated: boolean) => {
      const duration = animated ? CAMERA_DURATION_MS : 0
      if (coords.length === 0) {
        map.easeTo({ center: DEFAULT_CENTER, zoom: 11, duration })
        return
      }
      if (coords.length === 1) {
        map.easeTo({ center: coords[0], zoom: 14, duration })
        return
      }
      const bounds = new LngLatBounds(coords[0], coords[0])
      for (const point of coords) bounds.extend(point)
      map.fitBounds(bounds, {
        padding: { top: 64, bottom: 40, left: 48, right: 48 },
        maxZoom: 13.5,
        duration,
        essential: true,
      })
    }

    const renderPlaces: RenderPlaces = (dayPlaces, modes) => {
      const map = mapRef.current
      if (!map) return

      const coords = dayPlaces.map((place) => place.coordinates)
      const requestKey = [
        coords.map((c) => c.join(',')).join('|'),
        modes.map((mode) => mode ?? '').join('|'),
      ].join('::')

      markersRef.current.forEach((marker) => marker.remove())
      markersRef.current = dayPlaces.map((place, index) =>
        new Marker({ element: createPin(index + 1), anchor: 'center' })
          .setLngLat(place.coordinates)
          .addTo(map),
      )

      forceMapLayout(map)
      fitPlaces(map, coords, true)
      setRouteCoords(coords.length >= 2 ? [coords[0]] : coords)

      if (coords.length < 2) return

      routeAbortRef.current?.abort()
      const controller = new AbortController()
      routeAbortRef.current = controller

      void fetchRoadRoute(coords, modes, controller.signal)
        .then((road) => {
          if (cancelled || controller.signal.aborted) return
          const currentKey = [
            placesRef.current.map((place) => place.coordinates.join(',')).join('|'),
            legModesRef.current.map((mode) => mode ?? '').join('|'),
          ].join('::')
          if (currentKey !== requestKey) return
          animateRouteDraw(road)
        })
        .catch((error) => {
          if (error instanceof DOMException && error.name === 'AbortError') return
          if (cancelled || controller.signal.aborted) return
          animateRouteDraw(coords)
        })
    }

    renderPlacesRef.current = renderPlaces

    const mount = async () => {
      try {
        await waitForSize(container, abort.signal)
        if (cancelled) return

        ensureMapLibreWorker()
        container.replaceChildren()

        const map = new Map({
          container,
          style: BASEMAP_STYLE,
          center: DEFAULT_CENTER,
          zoom: 11,
          attributionControl: { compact: true },
          cooperativeGestures: true,
          fadeDuration: 0,
        })

        mapRef.current = map

        const { svg, path } = createRouteOverlay()
        routePathRef.current = path
        map.getContainer().appendChild(svg)

        const onCamera = () => redrawPath()
        map.on('move', onCamera)
        map.on('zoom', onCamera)
        map.on('resize', onCamera)
        cleanupFns.push(() => {
          map.off('move', onCamera)
          map.off('zoom', onCamera)
          map.off('resize', onCamera)
          svg.remove()
          routePathRef.current = null
        })

        const finish = () => {
          if (cancelled || markedReady) return
          markedReady = true
          if (pollId) window.clearInterval(pollId)
          forceMapLayout(map)
          setStatus('ready')
          timers.push(
            window.setTimeout(() => {
              if (!cancelled) {
                forceMapLayout(map)
                redrawPath()
              }
            }, 50),
          )
        }

        map.once('load', finish)
        map.once('idle', finish)

        pollId = window.setInterval(() => {
          if (cancelled) return
          if (map.loaded() || map.isStyleLoaded()) finish()
        }, 120)

        timers.push(window.setTimeout(finish, 2000))

        const observer = new ResizeObserver(() => {
          if (cancelled || !mapRef.current) return
          forceMapLayout(map)
          redrawPath()
          if (!markedReady && (map.loaded() || map.isStyleLoaded())) finish()
        })
        observer.observe(container)
        if (wrapRef.current) observer.observe(wrapRef.current)
        cleanupFns.push(() => observer.disconnect())
      } catch (error) {
        if (cancelled) return
        if (error instanceof DOMException && error.name === 'AbortError') return
        setStatus('error')
      }
    }

    void mount()

    return () => {
      cancelled = true
      abort.abort()
      if (pollId) window.clearInterval(pollId)
      timers.forEach((id) => window.clearTimeout(id))
      cleanupFns.forEach((fn) => fn())
      routeAbortRef.current?.abort()
      if (routeAnimRef.current) cancelAnimationFrame(routeAnimRef.current)
      renderPlacesRef.current = null
      markersRef.current.forEach((marker) => marker.remove())
      markersRef.current = []
      mapRef.current?.remove()
      mapRef.current = null
      routeCoordsRef.current = []
    }
  }, [])

  useEffect(() => {
    if (status !== 'ready') return
    renderPlacesRef.current?.(places, legModes)
  }, [places, legModes, status])

  return (
    <div ref={wrapRef} className={styles.wrap}>
      <div
        ref={containerRef}
        className={styles.map}
        role="img"
        aria-label={`Карта маршрута дня, ${places.length} ${pointsLabel(places.length)}`}
      />

      {status === 'loading' ? (
        <div className={styles.overlay} aria-hidden>
          <span className={styles.spinner} />
        </div>
      ) : null}

      {status === 'error' ? (
        <div className={styles.fallback}>
          <p className={styles.fallbackTitle}>Карта недоступна</p>
          <p className={styles.fallbackText}>Не удалось загрузить тайлы. Проверьте сеть и обновите страницу.</p>
        </div>
      ) : null}

      {status === 'ready' && places.length > 0 ? (
        <div className={styles.badge}>
          Маршрут дня · {places.length} {pointsLabel(places.length)}
        </div>
      ) : null}
    </div>
  )
}
