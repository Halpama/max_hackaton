import { describe, expect, it } from 'vitest'
import { parseOpeningHours } from './openingHours'

describe('parseOpeningHours', () => {
  it('parses an everyday range', () => {
    expect(parseOpeningHours('ежедневно 10:00–20:00')).toEqual([
      { days: 'Ежедневно', hours: '10:00–20:00' },
    ])
  })

  it('parses a weekday range', () => {
    expect(parseOpeningHours('вт–вс 10:00–17:30')).toEqual([
      { days: 'Вт–Вс', hours: '10:00–17:30' },
    ])
  })

  it('parses mixed lists and ranges', () => {
    expect(parseOpeningHours('пн, ср–вс 11:00–23:00')).toEqual([
      { days: 'Пн, Ср–Вс', hours: '11:00–23:00' },
    ])
  })

  it('drops parenthesised cashier notes', () => {
    expect(parseOpeningHours('ежедневно 10:00–20:00 (касса: ежедневно 10:00–19:15)')).toEqual([
      { days: 'Ежедневно', hours: '10:00–20:00' },
    ])
  })

  it('normalises dotted separators to en-dash', () => {
    expect(parseOpeningHours('ежедневно 10.00-20.00')).toEqual([
      { days: 'Ежедневно', hours: '10:00–20:00' },
    ])
  })

  it('falls back to everyday for a bare «весь день»', () => {
    expect(parseOpeningHours('весь день')).toEqual([{ days: 'Ежедневно', hours: 'Весь день' }])
  })

  it('returns an empty list for empty input', () => {
    expect(parseOpeningHours('')).toEqual([])
    expect(parseOpeningHours('   ')).toEqual([])
  })
})
