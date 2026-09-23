const trimSlash = (value: string) => value.replace(/\/+$/, '')

/**
 * Backend base URL.
 *
 * - Dev (recommended): leave `VITE_API_BASE_URL` empty → requests go to the
 *   same origin and Vite proxies `/api` to the backend. Works from an iPhone
 *   on the same Wi‑Fi without hardcoding a LAN IP.
 * - Absolute URL: `http://localhost:8000` or `http://192.168.x.x:8000` when
 *   you want to hit the API directly (Docker web build, etc.).
 */
export const API_BASE_URL = trimSlash(
  import.meta.env.VITE_API_BASE_URL?.trim() || '',
)

export const IS_DEV = import.meta.env.DEV

/**
 * Work offline against the bundled mock trip instead of the API.
 * Only when explicitly enabled — empty API_BASE_URL means same-origin proxy.
 */
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS?.trim() === 'true'

/** Free Yandex Maps Tiles API key — Russian basemap for MapLibre. */
export const YANDEX_MAPS_TILES_KEY =
  import.meta.env.VITE_YANDEX_MAPS_TILES_KEY?.trim() || ''
