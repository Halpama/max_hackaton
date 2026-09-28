import { describe, expect, it } from 'vitest'
import { routeForStartParam } from './startParam'

describe('routeForStartParam', () => {
  it('maps planner aliases to new trip', () => {
    expect(routeForStartParam('new')).toBe('/trips/new')
    expect(routeForStartParam('planner')).toBe('/trips/new')
    expect(routeForStartParam('NEW_trip')).toBe('/trips/new')
  })

  it('ignores unknown params', () => {
    expect(routeForStartParam(undefined)).toBeNull()
    expect(routeForStartParam('')).toBeNull()
    expect(routeForStartParam('settings')).toBeNull()
  })
})
