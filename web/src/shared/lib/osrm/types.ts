/** [longitude, latitude] */
export type LngLat = [number, number]

/** OSRM routing profile — chosen from backend transit mode */
export type RouteProfile = 'foot' | 'driving'

export type TransitModeLike = 'walk' | 'taxi' | 'metro' | string
