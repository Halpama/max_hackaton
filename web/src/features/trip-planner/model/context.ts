import { createContext } from "react";
import type {
    InterestId,
    Place,
    RoutePlan,
    TripDraft,
    TripPace,
    TripSummary,
} from "./types";

export type LoadState = "idle" | "loading" | "ready" | "error";

export interface TripPlannerContextValue {
    /** Wizard form state — only for create / edit-params screens. */
    draft: TripDraft;
    updateDraft: (patch: Partial<TripDraft>) => void;
    replaceDraft: (draft: TripDraft) => void;
    toggleInterest: (id: InterestId) => void;
    setPace: (pace: TripPace) => void;
    setAdults: (value: number) => void;
    setChildren: (value: number) => void;
    resetDraft: () => void;

    /** Trip currently open on /route and /places/:id. */
    activeTripId: string | null;
    /** Server params of the open trip (budget etc.) — not the wizard form. */
    activeTripDraft: TripDraft | null;
    route: RoutePlan | null;
    routeState: LoadState;
    routeError: string | null;
    openTrip: (tripId: string) => Promise<void>;
    adoptRoute: (tripId: string, route: RoutePlan) => void;

    trips: TripSummary[];
    tripsState: LoadState;
    refreshTrips: () => Promise<void>;
    /** Soft-hide a trip on the server (or locally in mock mode). */
    removeTrip: (tripId: string) => Promise<void>;

    favorites: Set<string>;
    favoritePlaces: Place[];
    toggleFavorite: (placeId: string) => void;
    isFavorite: (placeId: string) => boolean;

    /** Place from the open route or the favourites cache, if already loaded. */
    findPlace: (placeId: string) => Place | undefined;
}

export const TripPlannerContext = createContext<TripPlannerContextValue | null>(
    null,
);
