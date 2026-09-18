export type TripPace = 'calm' | 'medium' | 'active'

export type InterestId =
  | 'sights'
  | 'museums'
  | 'gastro'
  | 'walks'
  | 'nature'
  | 'unusual'

export interface TripDraft {
  destination: string
  startDate: string
  endDate: string
  budget: number
  travelers: number
  interests: InterestId[]
  pace: TripPace
  findHousing: boolean
}

export type TransitMode = 'walk' | 'taxi' | 'metro'

export interface TransitLeg {
  mode: TransitMode
  label: string
}

export interface Place {
  id: string
  title: string
  category: string
  categoryKind: 'museum' | 'location' | 'food' | 'walk'
  priceLabel: string
  priceValue?: number
  durationLabel: string
  timeRange: string
  rating: number
  reviewsLabel: string
  address: string
  description: string
  imageUrl: string
}

export interface Activity {
  id: string
  placeId: string
  time: string
  durationLabel: string
  title: string
  meta: string
}

export interface DayPlan {
  id: string
  label: string
  activities: Activity[]
  transits: Array<TransitLeg | null>
}

export interface RoutePlan {
  city: string
  dateLabel: string
  travelersLabel: string
  budgetLabel: string
  days: DayPlan[]
  places: Record<string, Place>
}
