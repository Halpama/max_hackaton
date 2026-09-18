const trimSlash = (value: string) => value.replace(/\/+$/, '')

/**
 * Base URL for the Python backend.
 * Set `VITE_API_BASE_URL` in `.env` / `.env.local` (e.g. http://localhost:8000).
 */
export const API_BASE_URL = trimSlash(
  import.meta.env.VITE_API_BASE_URL?.trim() || '',
)

export const IS_DEV = import.meta.env.DEV
