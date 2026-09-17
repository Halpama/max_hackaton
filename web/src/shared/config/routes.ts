export const ROUTES = {
  home: '/',
} as const

export type AppRoute = (typeof ROUTES)[keyof typeof ROUTES]
