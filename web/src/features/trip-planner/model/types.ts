/** Minimum trip length in hours. */
export const MIN_TRIP_DURATION_HOURS = 12;

/** Default trip length when the arrival date changes. */
export const DEFAULT_TRIP_DURATION_DAYS = 3;

export const MAX_TRIP_BUDGET = 9_999_999;

export type TripPace = "calm" | "medium" | "active";

export type InterestId =
    | "sights"
    | "museums"
    | "gastro"
    | "walks"
    | "nature"
    | "unusual";

export interface TripDraft {
    destination: string;
    startDate: string;
    startTime: string;
    endDate: string;
    endTime: string;
    budget: number;
    adults: number;
    children: number;
    interests: InterestId[];
    pace: TripPace;
    findHousing: boolean;
}

export type TripEditDraft = Omit<TripDraft, "destination">;

export type TransitMode = "walk" | "taxi" | "metro";

export interface TransitLeg {
    mode: TransitMode;
    label: string;
}

/** Whether the rating is a real catalogue signal or our own projection. */
export type RatingSource = "catalog" | "estimate";

/** Where a place is: indoors, outdoors, both, or not yet classified. */
export type EnvironmentKind = 'indoor' | 'outdoor' | 'mixed' | 'unknown'

export interface Place {
    id: string;
    title: string;
    category: string;
    categoryKind: "museum" | "location" | "food" | "walk";
    environmentKind?: EnvironmentKind
    city: string;
    priceLabel: string;
    priceValue?: number;
    /** True when we guessed the price — the UI must not present it as a fact. */
    priceEstimated?: boolean;
    durationLabel: string;
    timeRange: string;
    rating: number;
    reviewsLabel: string;
    ratingSource?: RatingSource;
    address: string;
    description: string;
    imageUrl: string;
    openingHours?: string | null;
    sourceUrl?: string | null;
    sourceName?: string | null;
    /** [longitude, latitude] */
    coordinates: [number, number];
}

export type TripStatus = TripGenerationStatus;

export interface TripSummary {
    id: string;
    city: string;
    dateLabel: string;
    travelersLabel: string;
    budgetLabel: string;
    status: TripStatus;
}

export interface Activity {
    id: string;
    placeId: string;
    time: string;
    durationLabel: string;
    title: string;
    meta: string;
}

export type WeatherIcon =
    | "clear"
    | "cloudy"
    | "fog"
    | "rain"
    | "sleet"
    | "snow"
    | "storm";

export interface DayWeather {
    label: string;
    icon: WeatherIcon;
    tempHigh: number;
    tempLow: number;
    precipitationChance?: number | null;
}

export interface DayPlan {
    id: string;
    label: string;
    date?: string | null;
    dateLabel?: string | null;
    activities: Activity[];
    transits: Array<TransitLeg | null>;
    /** Absent past the 16-day forecast horizon — show a placeholder, not a guess. */
    weather?: DayWeather | null;
}

export interface RoutePlan {
    city: string;
    dateLabel: string;
    travelersLabel: string;
    budgetLabel: string;
    cityGuide?: CityGuide | null;
    days: DayPlan[];
    places: Record<string, Place>;
}

export interface SeasonalityMonth {
    month: number;
    label: string;
    score: number;
    level: string;
    isTripMonth: boolean;
}

export interface CityGuide {
    type: string;
    summary: string;
    history: string;
    highlights: string[];
    tripMonth: number;
    tripMonthLabel: string;
    seasonality: SeasonalityMonth[];
    /** climate = Open-Meteo normals; profile = curated fallback */
    seasonalitySource?: string | null;
    imageUrl?: string | null;
    sourceUrl?: string | null;
    sourceName?: string | null;
}

/** Lifecycle of a trip on the backend, distinct from the `TripStatus` badge. */
export type TripGenerationStatus = "pending" | "running" | "ready" | "failed";

export interface TripCreated {
    id: string;
    status: TripGenerationStatus;
}

export interface TripDetails {
    id: string;
    status: TripGenerationStatus;
    stage: string | null;
    error: string | null;
    draft: TripDraft;
    route: RoutePlan | null;
}

/** One of the five generation stages, streamed over SSE while the route builds. */
export interface StageEvent {
    type: "stage";
    key: string;
    index: number;
    label: string;
    status: "active" | "done";
}

export interface DoneEvent {
    type: "done";
    tripId: string;
    route: RoutePlan;
}

export interface GenerationErrorEvent {
    type: "error";
    tripId: string;
    message: string;
    code: string;
}
