import {
  GeoJSONSource,
  LngLatBounds,
  Map,
  Marker,
  setWorkerUrl,
  type Map as MaplibreMap,
  type Marker as MaplibreMarker,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

let ready = false

/**
 * MapLibre v6 + Vite needs an explicit worker URL, otherwise the
 * prebundled `maplibre-gl-worker.mjs` request hangs forever.
 */
export function ensureMapLibreWorker() {
  if (ready) return
  setWorkerUrl(workerUrl)
  ready = true
}

export { GeoJSONSource, LngLatBounds, Map, Marker }
export type { MaplibreMap, MaplibreMarker }
