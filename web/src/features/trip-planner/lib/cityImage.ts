/**
 * City cover images for the trips list.
 *
 * Known cities ship with Wikipedia thumbs so the list paints instantly; anything
 * else is resolved via the free page-summary API on first open.
 */

/** Exact thumbnail URLs returned by ru.wikipedia page summary — verified live. */
const KNOWN: Record<string, string> = {
  'санкт-петербург':
    'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fd/Palace_Bridge_SPB_%28img2%29_Crop.jpg/330px-Palace_Bridge_SPB_%28img2%29_Crop.jpg',
  петербург:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fd/Palace_Bridge_SPB_%28img2%29_Crop.jpg/330px-Palace_Bridge_SPB_%28img2%29_Crop.jpg',
  москва:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/0/01/Moscow_July_2011-16.jpg/330px-Moscow_July_2011-16.jpg',
  казань:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/Kazan_Kremlin._Qol%C5%9F%C3%A4rif_Mosque_P8111875_2200.jpg/330px-Kazan_Kremlin._Qol%C5%9F%C3%A4rif_Mosque_P8111875_2200.jpg',
  сочи:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/Sochi_Marina.jpg/330px-Sochi_Marina.jpg',
  'нижний новгород':
    'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Nizhny_Novgorod_2025-04-29_Minin_and_Pozharsky_square_01.jpg/330px-Nizhny_Novgorod_2025-04-29_Minin_and_Pozharsky_square_01.jpg',
  екатеринбург:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/%D0%93%D0%BE%D1%80%D1%81%D0%BE%D0%B2%D0%B5%D1%82_%D0%90%D0%B4%D0%BC%D0%B8%D0%BD%D0%B8%D1%81%D1%82%D1%80%D0%B0%D1%86%D0%B8%D1%8F_%D0%95%D0%BA%D0%B0%D1%82%D0%B5%D1%80%D0%B8%D0%BD%D0%B1%D1%83%D1%80%D0%B3%D0%B0.jpg/330px-%D0%93%D0%BE%D1%80%D1%81%D0%BE%D0%B2%D0%B5%D1%82_%D0%90%D0%B4%D0%BC%D0%B8%D0%BD%D0%B8%D1%81%D1%82%D1%80%D0%B0%D1%86%D0%B8%D1%8F_%D0%95%D0%BA%D0%B0%D1%82%D0%B5%D1%80%D0%B8%D0%BD%D0%B1%D1%83%D1%80%D0%B3%D0%B0.jpg',
  новосибирск:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Opera-and-Ballet-theatre-Novosibirsk.jpg/330px-Opera-and-Ballet-theatre-Novosibirsk.jpg',
  самара:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/%D0%9C%D0%BE%D0%BD%D1%83%D0%BC%D0%B5%D0%BD%D1%82_%D0%A1%D0%BB%D0%B0%D0%B2%D1%8B_%D0%A1%D0%B0%D0%BC%D0%B0%D1%80%D0%B0.jpg/330px-%D0%9C%D0%BE%D0%BD%D1%83%D0%BC%D0%B5%D0%BD%D1%82_%D0%A1%D0%BB%D0%B0%D0%B2%D1%8B_%D0%A1%D0%B0%D0%BC%D0%B0%D1%80%D0%B0.jpg',
  краснодар:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/%D0%A2%D1%80%D0%B8%D1%83%D0%BC%D1%84%D0%B0%D0%BB%D1%8C%D0%BD%D0%B0%D1%8F_%D0%B0%D1%80%D0%BA%D0%B0_%D0%B8_%D0%BF%D0%B0%D0%BC%D1%8F%D1%82%D0%BD%D0%B8%D0%BA_%D0%A1%D0%B2%D1%8F%D1%82%D0%BE%D0%B9_%D0%95%D0%BA%D0%B0%D1%82%D0%B5%D1%80%D0%B8%D0%BD%D0%B5_%281%29.jpg/330px-%D0%A2%D1%80%D0%B8%D1%83%D0%BC%D1%84%D0%B0%D0%BB%D1%8C%D0%BD%D0%B0%D1%8F_%D0%B0%D1%80%D0%BA%D0%B0_%D0%B8_%D0%BF%D0%B0%D0%BC%D1%8F%D1%82%D0%BD%D0%B8%D0%BA_%D0%A1%D0%B2%D1%8F%D1%82%D0%BE%D0%B9_%D0%95%D0%BA%D0%B0%D1%82%D0%B5%D1%80%D0%B8%D0%BD%D0%B5_%281%29.jpg',
  уфа:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/%D0%94%D0%BE%D0%BC_%D0%B6%D0%B8%D0%BB%D0%BE%D0%B9_%D0%9D%D0%B0%D0%B3%D0%B0%D1%80%D0%B5%D0%B2%D0%B0%2C_%D0%A3%D1%84%D0%B0.jpg/330px-%D0%94%D0%BE%D0%BC_%D0%B6%D0%B8%D0%BB%D0%BE%D0%B9_%D0%9D%D0%B0%D0%B3%D0%B0%D1%80%D0%B5%D0%B2%D0%B0%2C_%D0%A3%D1%84%D0%B0.jpg',
  красноярск:
    'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/%D0%9A%D1%80%D0%B0%D1%81%D0%BD%D0%BE%D1%8F%D1%80%D1%81%D0%BA_%D0%A1%D1%82%D1%80%D0%B5%D0%BB%D0%BA%D0%B0_%D1%81_%D0%B2%D1%8B%D1%81%D0%BE%D1%82%D1%8B.jpg/330px-%D0%9A%D1%80%D0%B0%D1%81%D0%BD%D0%BE%D1%8F%D1%80%D1%81%D0%BA_%D0%A1%D1%82%D1%80%D0%B5%D0%BB%D0%BA%D0%B0_%D1%81_%D0%B2%D1%8B%D1%81%D0%BE%D1%82%D1%8B.jpg',
}

const cache = new Map<string, string | null>()
const inflight = new Map<string, Promise<string | null>>()

function normalize(city: string): string {
  return city.trim().toLowerCase().replace(/^г\.\s*/u, '')
}

/** Synchronous lookup for the cities we ship with — paints without a flash. */
export function knownCityImage(city: string): string | null {
  return KNOWN[normalize(city)] ?? null
}

/** Resolve a cover image, falling back to the Wikipedia page summary. */
export async function resolveCityImage(city: string): Promise<string | null> {
  const key = normalize(city)
  if (!key) return null

  const known = KNOWN[key]
  if (known) return known

  if (cache.has(key)) return cache.get(key) ?? null

  const pending = inflight.get(key)
  if (pending) return pending

  const task = fetchWikipediaThumb(city)
    .then((url) => {
      cache.set(key, url)
      inflight.delete(key)
      return url
    })
    .catch(() => {
      cache.set(key, null)
      inflight.delete(key)
      return null
    })

  inflight.set(key, task)
  return task
}

async function fetchWikipediaThumb(city: string): Promise<string | null> {
  const title = encodeURIComponent(city.trim())
  const response = await fetch(
    `https://ru.wikipedia.org/api/rest_v1/page/summary/${title}`,
    {
      headers: {
        Accept: 'application/json',
        'Api-User-Agent': 'TripPlannerMAX/1.0 (hackathon)',
      },
    },
  )
  if (!response.ok) return null
  const data = (await response.json()) as {
    thumbnail?: { source?: string }
    originalimage?: { source?: string }
  }
  const raw = data.thumbnail?.source || data.originalimage?.source || null
  return raw ? cleanThumbUrl(raw) : null
}

function cleanThumbUrl(url: string): string {
  return url
    .replace('https://thumb.wikimedia.org/', 'https://upload.wikimedia.org/')
    .replace(/\?.*$/, '')
}
