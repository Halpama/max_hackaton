export function isNullable(value: unknown): value is null | undefined {
  return value === null || value === undefined
}

export function compact<T>(values: Array<T | null | undefined | false | ''>): T[] {
  return values.filter((value): value is T => Boolean(value))
}

export function getUserDisplayName(user?: {
  first_name?: string
  last_name?: string
  username?: string
}): string {
  if (!user) {
    return 'Гость'
  }

  const fullName = compact([user.first_name, user.last_name]).join(' ')
  return fullName || user.username || 'Гость'
}

export function getUserInitials(user?: {
  first_name?: string
  last_name?: string
  username?: string
}): string {
  if (!user) {
    return '?'
  }

  const fromName = compact([user.first_name?.[0], user.last_name?.[0]])
    .join('')
    .toUpperCase()

  if (fromName) {
    return fromName
  }

  return user.username?.[0]?.toUpperCase() ?? '?'
}
