import { ROUTES } from '@/shared/config'

const CONSUMED_KEY = '2rist:start_param_consumed'

/** Map MAX `start_param` / startapp payload → in-app route. */
export function routeForStartParam(raw: string | undefined | null): string | null {
  if (!raw) return null
  const value = raw.trim().toLowerCase()
  if (!value) return null

  if (
    value === 'new' ||
    value === 'planner' ||
    value === 'trip' ||
    value === 'trips/new' ||
    value.startsWith('new_')
  ) {
    return ROUTES.newTrip
  }

  return null
}

/** Consume start_param once per browser session so refresh does not loop. */
export function takeStartParamRoute(raw: string | undefined | null): string | null {
  const route = routeForStartParam(raw)
  if (!route) return null
  try {
    if (sessionStorage.getItem(CONSUMED_KEY) === raw) return null
    sessionStorage.setItem(CONSUMED_KEY, raw ?? '')
  } catch {
    // private mode / blocked storage — still navigate once this mount
  }
  return route
}
