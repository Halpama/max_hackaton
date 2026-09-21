import { api } from '@/shared/api'
import type { Place } from '../model/types'

export function getPlace(placeId: string) {
  return api.get<Place>(`/api/v1/places/${placeId}`, { withInitData: true })
}

export function listFavorites() {
  return api.get<Place[]>('/api/v1/favorites', { withInitData: true })
}

export function addFavorite(placeId: string) {
  return api.put<void>(`/api/v1/favorites/${placeId}`, undefined, {
    withInitData: true,
  })
}

export function removeFavorite(placeId: string) {
  return api.delete<void>(`/api/v1/favorites/${placeId}`, { withInitData: true })
}
