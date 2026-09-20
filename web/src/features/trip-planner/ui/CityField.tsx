import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { api } from '@/shared/api'
import { USE_MOCKS } from '@/shared/config'
import { SearchIcon } from './icons'
import styles from './CityField.module.css'

export type CitySuggestion = {
  name: string
  subtitle: string
  label: string
}

const FALLBACK_CITIES: CitySuggestion[] = [
  { name: 'Москва', subtitle: 'Россия', label: 'Москва' },
  { name: 'Санкт-Петербург', subtitle: 'Россия', label: 'Санкт-Петербург' },
  { name: 'Казань', subtitle: 'Татарстан, Россия', label: 'Казань' },
  { name: 'Сочи', subtitle: 'Краснодарский край, Россия', label: 'Сочи' },
  { name: 'Екатеринбург', subtitle: 'Свердловская область, Россия', label: 'Екатеринбург' },
  { name: 'Нижний Новгород', subtitle: 'Россия', label: 'Нижний Новгород' },
  { name: 'Калининград', subtitle: 'Россия', label: 'Калининград' },
  { name: 'Владивосток', subtitle: 'Россия', label: 'Владивосток' },
]

async function fetchSuggestions(query: string): Promise<CitySuggestion[]> {
  if (USE_MOCKS) {
    const q = query.trim().toLowerCase()
    if (q.length < 2) return FALLBACK_CITIES
    return FALLBACK_CITIES.filter((city) => city.name.toLowerCase().includes(q))
  }
  const data = await api.get<{ items: CitySuggestion[] }>(
    `/api/v1/geo/cities?q=${encodeURIComponent(query)}`,
  )
  return data.items ?? []
}

type CityFieldProps = {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

type MenuBox = { top: number; left: number; width: number }

export function CityField({ value, onChange, placeholder = 'Город' }: CityFieldProps) {
  const listId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLUListElement>(null)
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<CitySuggestion[]>(FALLBACK_CITIES)
  const [loading, setLoading] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const [box, setBox] = useState<MenuBox | null>(null)

  const syncBox = () => {
    const node = rootRef.current
    if (!node) return
    const rect = node.getBoundingClientRect()
    setBox({
      top: rect.bottom + 6,
      left: rect.left,
      width: rect.width,
    })
  }

  useLayoutEffect(() => {
    if (!open) {
      setBox(null)
      return
    }
    syncBox()
  }, [open, items.length])

  useEffect(() => {
    if (!open) return
    const onReposition = () => syncBox()
    window.addEventListener('resize', onReposition)
    window.addEventListener('scroll', onReposition, true)
    return () => {
      window.removeEventListener('resize', onReposition)
      window.removeEventListener('scroll', onReposition, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const onPointer = (event: MouseEvent) => {
      const target = event.target as Node
      if (rootRef.current?.contains(target)) return
      if (menuRef.current?.contains(target)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    return () => document.removeEventListener('mousedown', onPointer)
  }, [open])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    const handle = window.setTimeout(() => {
      setLoading(true)
      void fetchSuggestions(value)
        .then((next) => {
          if (cancelled) return
          const q = value.trim()
          // Do not fall back to popular cities mid-search — that resurrects
          // villages the API already filtered out.
          setItems(next.length ? next : q.length < 2 ? FALLBACK_CITIES : [])
          setHighlight(0)
        })
        .catch(() => {
          if (cancelled) return
          const q = value.trim().toLowerCase()
          setItems(
            q.length < 2
              ? FALLBACK_CITIES
              : FALLBACK_CITIES.filter((city) => city.name.toLowerCase().includes(q)),
          )
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 220)
    return () => {
      cancelled = true
      window.clearTimeout(handle)
    }
  }, [value, open])

  const pick = (city: CitySuggestion) => {
    onChange(city.name)
    setOpen(false)
  }

  return (
    <div className={styles.root} ref={rootRef}>
      <label className={styles.field}>
        <span className={styles.icon} aria-hidden>
          <SearchIcon />
        </span>
        <input
          className={styles.input}
          value={value}
          placeholder={placeholder}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            onChange(event.target.value)
            setOpen(true)
          }}
          onKeyDown={(event) => {
            if (!open || items.length === 0) return
            if (event.key === 'ArrowDown') {
              event.preventDefault()
              setHighlight((prev) => (prev + 1) % items.length)
            } else if (event.key === 'ArrowUp') {
              event.preventDefault()
              setHighlight((prev) => (prev - 1 + items.length) % items.length)
            } else if (event.key === 'Enter') {
              event.preventDefault()
              const city = items[highlight]
              if (city) pick(city)
            } else if (event.key === 'Escape') {
              setOpen(false)
            }
          }}
        />
      </label>

      {open && box
        ? createPortal(
            <ul
              ref={menuRef}
              className={styles.dropdown}
              id={listId}
              role="listbox"
              style={{
                top: box.top,
                left: box.left,
                width: box.width,
              }}
            >
              {loading && items.length === 0 ? (
                <li className={styles.empty}>Ищем города…</li>
              ) : null}
              {items.map((city, index) => (
                <li key={`${city.name}-${city.subtitle}`}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={index === highlight}
                    className={index === highlight ? styles.optionActive : styles.option}
                    onMouseEnter={() => setHighlight(index)}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => pick(city)}
                  >
                    <span className={styles.optionName}>{city.name}</span>
                    {city.subtitle ? (
                      <span className={styles.optionMeta}>{city.subtitle}</span>
                    ) : null}
                  </button>
                </li>
              ))}
              {!loading && items.length === 0 ? (
                <li className={styles.empty}>Ничего не нашлось</li>
              ) : null}
            </ul>,
            document.body,
          )
        : null}
    </div>
  )
}
