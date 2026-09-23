export function formatBudget(value: number): string {
  return value.toLocaleString('ru-RU')
}

/** Local calendar day as YYYY-MM-DD (noon to avoid DST edge cases). */
export function localDateIso(offsetDays = 0): string {
  const d = new Date()
  d.setHours(12, 0, 0, 0)
  d.setDate(d.getDate() + offsetDays)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Capitalise the first letter — catalogues often ship lowercase Russian titles. */
export function formatPlaceTitle(title: string): string {
  const trimmed = title.trim().replace(/\s+/g, ' ')
  if (!trimmed) return trimmed
  for (let i = 0; i < trimmed.length; i += 1) {
    const ch = trimmed[i]!
    if (/\p{L}/u.test(ch)) {
      if (ch === ch.toLowerCase() && ch !== ch.toUpperCase()) {
        return trimmed.slice(0, i) + ch.toUpperCase() + trimmed.slice(i + 1)
      }
      return trimmed
    }
  }
  return trimmed
}

export function formatTravelers(count: number): string {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return `${count} человек`
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} человека`
  }
  return `${count} человек`
}

export function formatShortDate(iso: string): string {
  const date = new Date(`${iso}T12:00:00`)
  const formatted = date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  return formatted.replace(/\./g, '')
}

export function formatTime(value: string): string {
  const match = /^(\d{1,2}):(\d{2})$/.exec(value.trim())
  if (!match) return value
  return `${match[1].padStart(2, '0')}:${match[2]}`
}

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

/** Local datetime from ISO date + HH:mm. */
export function dateTimeToMs(date: string, time: string): number {
  const normalized = formatTime(time)
  return new Date(`${date}T${normalized}:00`).getTime()
}

export function msToDateTime(ms: number): { date: string; time: string } {
  const d = new Date(ms)
  return {
    date: `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`,
    time: `${pad2(d.getHours())}:${pad2(d.getMinutes())}`,
  }
}

export function shiftDateTime(
  date: string,
  time: string,
  hours: number,
): { date: string; time: string } {
  return msToDateTime(dateTimeToMs(date, time) + hours * 3_600_000)
}
