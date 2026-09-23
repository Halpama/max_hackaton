/** [longitude, latitude] — same as Place.coordinates */
export type LngLat = [number, number]

function latLon(coord: LngLat) {
  const [lng, lat] = coord
  return `${lat},${lng}`
}

/**
 * Open a single point on Yandex Maps (pin at the place, not an address search).
 * `ll` / `pt` use lon,lat — same order as Place.coordinates.
 */
export function yandexMapsPointUrl(coord: LngLat, zoom = 16) {
  const [lng, lat] = coord
  const params = new URLSearchParams({
    ll: `${lng},${lat}`,
    pt: `${lng},${lat}`,
    z: String(zoom),
  })
  return `https://yandex.ru/maps/?${params.toString()}`
}

/**
 * Yandex Maps route link.
 * rtext uses lat,lon; rtt: pd=walk, auto=car, mt=transit
 */
export function yandexMapsRouteUrl(
  from: LngLat,
  to: LngLat,
  mode: 'walk' | 'taxi' | 'metro' | string,
) {
  const rtt = mode === 'taxi' ? 'auto' : mode === 'metro' ? 'mt' : 'pd'
  const params = new URLSearchParams({
    rtext: `${latLon(from)}~${latLon(to)}`,
    rtt,
  })
  return `https://yandex.ru/maps/?${params.toString()}`
}

/**
 * Yandex Go (taxi) deeplink with A→B filled in.
 * Opens the app when installed, otherwise store / web.
 */
export function yandexGoRouteUrl(from: LngLat, to: LngLat) {
  const [startLon, startLat] = from
  const [endLon, endLat] = to
  const params = new URLSearchParams({
    'start-lat': String(startLat),
    'start-lon': String(startLon),
    'end-lat': String(endLat),
    'end-lon': String(endLon),
    ref: 'tripplanner',
    // Prefer Go website over store when app is missing (better for WebApp demos)
    appmetrica_tracking_id: '25395763362139037',
  })
  return `https://3.redirect.appmetrica.yandex.com/route?${params.toString()}`
}
