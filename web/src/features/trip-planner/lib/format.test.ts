import { describe, expect, it } from 'vitest'
import {
  formatBudget,
  formatPlaceTitle,
  formatTime,
  formatTravelers,
  localDateIso,
} from './format'

describe('formatBudget', () => {
  it('groups thousands with ru-RU separators', () => {
    expect(formatBudget(45_000)).toBe((45_000).toLocaleString('ru-RU'))
    expect(formatBudget(0)).toBe('0')
  })
})

describe('formatTravelers', () => {
  it.each([
    [1, '1 человек'],
    [2, '2 человека'],
    [4, '4 человека'],
    [5, '5 человек'],
    [11, '11 человек'],
    [21, '21 человек'],
    [22, '22 человека'],
    [0, '0 человек'],
  ])('%i → %s', (count, expected) => {
    expect(formatTravelers(count)).toBe(expected)
  })
})

describe('formatPlaceTitle', () => {
  it('capitalises a lowercase Russian title', () => {
    expect(formatPlaceTitle('эрмитаж')).toBe('Эрмитаж')
  })

  it('keeps an already-capitalised title and collapses spaces', () => {
    expect(formatPlaceTitle('  Государственный   Эрмитаж ')).toBe('Государственный Эрмитаж')
  })

  it('returns empty input unchanged', () => {
    expect(formatPlaceTitle('   ')).toBe('')
  })
})

describe('formatTime', () => {
  it('pads a single-digit hour', () => {
    expect(formatTime('9:05')).toBe('09:05')
    expect(formatTime('14:30')).toBe('14:30')
  })

  it('passes through invalid values', () => {
    expect(formatTime('bad')).toBe('bad')
  })
})

describe('localDateIso', () => {
  it('returns a calendar date in YYYY-MM-DD', () => {
    expect(localDateIso()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(localDateIso(1)).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})
