export function formatBudget(value: number): string {
  return value.toLocaleString('ru-RU')
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
  })
  return formatted.replace('.', '')
}
