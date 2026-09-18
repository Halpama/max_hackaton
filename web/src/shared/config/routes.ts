export const ROUTES = {
  home: '/',
  newTrip: '/trips/new',
  preferences: '/preferences',
  loading: '/loading',
  route: '/route',
  place: (placeId: string) => `/places/${placeId}`,
  placePattern: '/places/:placeId',
} as const

export type AppRoute = (typeof ROUTES)[keyof typeof ROUTES]
