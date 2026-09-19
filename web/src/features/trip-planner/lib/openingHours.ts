/**
 * Turn free-text Russian opening hours (KudaGo, OSM) into scannable rows.
 *
 * Examples we see in the wild:
 *   "ежедневно 10:00–20:00"
 *   "вт–вс 10:00–17:30"
 *   "пн, ср–вс 11:00–23:00"
 *   "пн–чт 11:00–1:00, пт 11:00–2:00, сб 12:00–2:00, вс 12:00–1:00"
 *   "ежедневно 10:00–20:00 (касса: ежедневно 10:00–19:15)"
 *   "ежедневно весь день"
 */

export interface OpeningHoursRow {
  days: string
  hours: string
}

const DAY_TOKEN =
  '(?:ежедневно|ежедн\\.?|пн|вт|ср|чт|пт|сб|вс|понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)'

const DAYS_PART = `${DAY_TOKEN}(?:\\s*[–\\-—,и]\\s*${DAY_TOKEN})*`
const TIME = '\\d{1,2}[:.]\\d{2}'
const HOURS_PART = `(?:весь\\s+день|круглосуточно|${TIME}\\s*[–\\-—]\\s*${TIME})`

const SEGMENT_RE = new RegExp(`(${DAYS_PART})\\s+(${HOURS_PART})`, 'giu')

const DAY_SHORT: Record<string, string> = {
  ежедневно: 'Ежедневно',
  ежедн: 'Ежедневно',
  понедельник: 'Пн',
  вторник: 'Вт',
  среда: 'Ср',
  четверг: 'Чт',
  пятница: 'Пт',
  суббота: 'Сб',
  воскресенье: 'Вс',
  пн: 'Пн',
  вт: 'Вт',
  ср: 'Ср',
  чт: 'Чт',
  пт: 'Пт',
  сб: 'Сб',
  вс: 'Вс',
}

export function parseOpeningHours(raw: string): OpeningHoursRow[] {
  const cleaned = raw
    .replace(/\([^)]*\)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  if (!cleaned) return []

  const rows: OpeningHoursRow[] = []
  for (const match of cleaned.matchAll(SEGMENT_RE)) {
    rows.push({
      days: prettifyDays(match[1]),
      hours: prettifyHours(match[2]),
    })
  }

  if (rows.length > 0) return rows

  // Single "весь день" / "круглосуточно" without an explicit day range.
  if (/весь\s+день|круглосуточно/i.test(cleaned)) {
    return [{ days: 'Ежедневно', hours: 'Весь день' }]
  }

  return [{ days: '', hours: cleaned }]
}

function prettifyDays(value: string): string {
  const lower = value.toLowerCase().trim()
  if (lower.startsWith('ежедн')) return 'Ежедневно'

  return lower
    .split(/\s*([–\-—,])\s*|\s+и\s+/u)
    .filter((part) => part != null && part !== '')
    .map((part) => {
      if (part === '-' || part === '—' || part === '–') return '–'
      if (part === ',') return ','
      return DAY_SHORT[part] ?? capitalize(part)
    })
    .join('')
    .replace(/,\s*/g, ', ')
    .replace(/\s*–\s*/g, '–')
}

function prettifyHours(value: string): string {
  const lower = value.toLowerCase().trim()
  if (lower.includes('весь') || lower.includes('круглосуточно')) return 'Весь день'
  return value.replace(/\./g, ':').replace(/\s*[–\-—]\s*/g, '–')
}

function capitalize(value: string): string {
  if (!value) return value
  return value[0].toUpperCase() + value.slice(1)
}
