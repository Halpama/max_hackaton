import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
    type ReactNode,
} from "react";
import { USE_MOCKS } from "@/shared/config";
import {
    addFavorite,
    deleteTrip,
    getTrip,
    listFavorites,
    listTrips,
    removeFavorite,
} from "../api";
import { TripPlannerContext, type LoadState } from "./context";
import { MOCK_ROUTE, MOCK_TRIPS, createDefaultTripDraft } from "./mock";
import {
    DEFAULT_TRIP_DURATION_DAYS,
    MAX_TRIP_BUDGET,
    MIN_TRIP_DURATION_HOURS,
    type InterestId,
    type Place,
    type RoutePlan,
    type TripDraft,
    type TripPace,
    type TripSummary,
} from "./types";
import { dateTimeToMs, localDateIso, shiftDateTime } from "../lib/format";

const ACTIVE_TRIP_KEY = "tp-active-trip";
const MIN_TRIP_MS = MIN_TRIP_DURATION_HOURS * 3_600_000;
const DEFAULT_TRIP_HOURS = DEFAULT_TRIP_DURATION_DAYS * 24;

function readActiveTripId(): string | null {
    try {
        return localStorage.getItem(ACTIVE_TRIP_KEY);
    } catch {
        return null;
    }
}

function persistActiveTripId(tripId: string | null) {
    try {
        if (tripId) localStorage.setItem(ACTIVE_TRIP_KEY, tripId);
        else localStorage.removeItem(ACTIVE_TRIP_KEY);
    } catch {
        // Private mode — the trip id simply will not survive a reload.
    }
}

function endFromStart(date: string, time: string) {
    return shiftDateTime(date, time, DEFAULT_TRIP_HOURS);
}

function applyDraftPatch(
    patch: Partial<TripDraft>,
    prev: TripDraft,
): TripDraft {
    const next: TripDraft = { ...prev, ...patch };

    if (typeof patch.budget === "number") {
        next.budget = Math.min(
            MAX_TRIP_BUDGET,
            Math.max(0, Math.floor(patch.budget)),
        );
    }

    const today = localDateIso();
    // Quietly block past arrival dates — no red error copy.
    if (next.startDate < today) {
        next.startDate = today;
    }

    const touchedStart = patch.startDate != null || patch.startTime != null;
    const touchedEnd = patch.endDate != null || patch.endTime != null;

    // Arrival drives departure: always snap end to start + 3 days.
    if (touchedStart && !touchedEnd) {
        const adjusted = endFromStart(next.startDate, next.startTime);
        next.endDate = adjusted.date;
        next.endTime = adjusted.time;
        return next;
    }

    const startMs = dateTimeToMs(next.startDate, next.startTime);
    const endMs = dateTimeToMs(next.endDate, next.endTime);
    if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) return next;

    // End too early / too short → quietly restore the default window.
    if (endMs - startMs < MIN_TRIP_MS) {
        const adjusted = endFromStart(next.startDate, next.startTime);
        next.endDate = adjusted.date;
        next.endTime = adjusted.time;
    }

    return next;
}

export function TripPlannerProvider({ children }: { children: ReactNode }) {
    const [draft, setDraft] = useState<TripDraft>(() =>
        createDefaultTripDraft(),
    );

    const [activeTripId, setActiveTripId] = useState<string | null>(() =>
        USE_MOCKS ? "mock" : readActiveTripId(),
    );
    const [activeTripDraft, setActiveTripDraft] = useState<TripDraft | null>(
        () => (USE_MOCKS ? createDefaultTripDraft() : null),
    );
    const [route, setRoute] = useState<RoutePlan | null>(
        USE_MOCKS ? MOCK_ROUTE : null,
    );
    const [routeState, setRouteState] = useState<LoadState>(
        USE_MOCKS ? "ready" : "idle",
    );
    const [routeError, setRouteError] = useState<string | null>(null);

    const [trips, setTrips] = useState<TripSummary[]>(
        USE_MOCKS ? MOCK_TRIPS : [],
    );
    const [tripsState, setTripsState] = useState<LoadState>(
        USE_MOCKS ? "ready" : "idle",
    );

    const [favoritePlaces, setFavoritePlaces] = useState<Place[]>([]);
    const [favorites, setFavorites] = useState<Set<string>>(() => new Set());

    // Guards against a slow response for a trip the user already navigated away from.
    const routeRequestRef = useRef(0);
    // Drops stale listFavorites responses so a slow mount fetch cannot wipe an optimistic toggle.
    const favoritesEpochRef = useRef(0);
    const favoritesRef = useRef(favorites);
    favoritesRef.current = favorites;
    const routeRef = useRef(route);
    routeRef.current = route;
    const draftRef = useRef(draft);
    draftRef.current = draft;
    const favoritePlacesRef = useRef(favoritePlaces);
    favoritePlacesRef.current = favoritePlaces;

    const updateDraft = useCallback((patch: Partial<TripDraft>) => {
        setDraft((prev) => applyDraftPatch(patch, prev));
    }, []);

    const replaceDraft = useCallback((next: TripDraft) => {
        setDraft(next);
    }, []);

    const toggleInterest = useCallback((id: InterestId) => {
        setDraft((prev) => {
            const exists = prev.interests.includes(id);
            return {
                ...prev,
                interests: exists
                    ? prev.interests.filter((item) => item !== id)
                    : [...prev.interests, id],
            };
        });
    }, []);

    const setPace = useCallback((pace: TripPace) => {
        setDraft((prev) => ({ ...prev, pace }));
    }, []);

    const setAdults = useCallback((value: number) => {
        setDraft((prev) => ({
            ...prev,
            adults: Math.min(10 - prev.children, Math.max(1, value)),
        }));
    }, []);

    const setChildren = useCallback((value: number) => {
        setDraft((prev) => ({
            ...prev,
            children: Math.min(10 - prev.adults, Math.max(0, value)),
        }));
    }, []);

    const resetDraft = useCallback(() => {
        setDraft(createDefaultTripDraft());
    }, []);

    const refreshTrips = useCallback(async () => {
        if (USE_MOCKS) return;

        setTripsState((prev) => (prev === "ready" ? prev : "loading"));
        try {
            setTrips(await listTrips());
            setTripsState("ready");
        } catch {
            setTripsState("error");
        }
    }, []);

    const removeTrip = useCallback(
        async (tripId: string) => {
            setTrips((prev) => prev.filter((trip) => trip.id !== tripId));

            if (activeTripId === tripId) {
                setActiveTripId(null);
                persistActiveTripId(null);
                setActiveTripDraft(null);
                setRoute(null);
                setRouteState("idle");
                setRouteError(null);
            }

            if (USE_MOCKS) return;

            try {
                await deleteTrip(tripId);
            } catch {
                await refreshTrips();
                throw new Error("delete_failed");
            }
        },
        [activeTripId, refreshTrips],
    );

    const refreshFavorites = useCallback(async () => {
        if (USE_MOCKS) return;

        const epoch = ++favoritesEpochRef.current;
        try {
            const places = await listFavorites();
            if (epoch !== favoritesEpochRef.current) return;
            setFavoritePlaces(places);
            setFavorites(new Set(places.map((place) => place.id)));
        } catch {
            // Favourites are non-critical; keep whatever is already on screen.
        }
    }, []);

    const openTrip = useCallback(async (tripId: string) => {
        if (USE_MOCKS) return;

        const requestId = routeRequestRef.current + 1;
        routeRequestRef.current = requestId;

        setActiveTripId(tripId);
        persistActiveTripId(tripId);
        setRouteState("loading");
        setRouteError(null);

        try {
            const trip = await getTrip(tripId);
            if (routeRequestRef.current !== requestId) return;

            if (trip.route) {
                setRoute(trip.route);
                setActiveTripDraft(trip.draft);
                setRouteState("ready");
            } else {
                setRoute(null);
                setActiveTripDraft(trip.draft);
                setRouteState("error");
                setRouteError(trip.error ?? "Маршрут ещё не построен");
            }
        } catch {
            if (routeRequestRef.current !== requestId) return;
            setRoute(null);
            setRouteState("error");
            setRouteError("Не удалось загрузить маршрут");
        }
    }, []);

    /** Adopt a route from SSE, keep its params for the open trip, clear the wizard. */
    const adoptRoute = useCallback((tripId: string, next: RoutePlan) => {
        routeRequestRef.current += 1;
        setActiveTripId(tripId);
        persistActiveTripId(tripId);
        setRoute(next);
        setRouteState("ready");
        setRouteError(null);
        setActiveTripDraft(draftRef.current);
        setDraft(createDefaultTripDraft());
    }, []);

    const toggleFavorite = useCallback((placeId: string) => {
        const wasFavorite = favoritesRef.current.has(placeId);
        // Invalidate in-flight list fetches so they cannot wipe this toggle.
        favoritesEpochRef.current += 1;
        const toggleEpoch = favoritesEpochRef.current;

        const resolvePlace = (): Place | undefined =>
            routeRef.current?.places[placeId] ??
            favoritePlacesRef.current.find((item) => item.id === placeId) ??
            (USE_MOCKS ? MOCK_ROUTE.places[placeId] : undefined);

        // Flip immediately — do not wait for the network round-trip.
        setFavorites((prev) => {
            const next = new Set(prev);
            if (wasFavorite) next.delete(placeId);
            else next.add(placeId);
            return next;
        });

        setFavoritePlaces((prev) => {
            if (wasFavorite) return prev.filter((item) => item.id !== placeId);
            if (prev.some((item) => item.id === placeId)) return prev;
            const place = resolvePlace();
            return place ? [place, ...prev] : prev;
        });

        if (USE_MOCKS) return;

        const request = wasFavorite
            ? removeFavorite(placeId)
            : addFavorite(placeId);
        request.catch(() => {
            if (toggleEpoch !== favoritesEpochRef.current) return;
            // Only the mutate call failed — roll back so the UI matches the server.
            setFavorites((prev) => {
                const next = new Set(prev);
                if (wasFavorite) next.add(placeId);
                else next.delete(placeId);
                return next;
            });
            setFavoritePlaces((prev) => {
                if (!wasFavorite)
                    return prev.filter((item) => item.id !== placeId);
                const place = resolvePlace();
                if (!place || prev.some((item) => item.id === placeId))
                    return prev;
                return [place, ...prev];
            });
        });
    }, []);

    const isFavorite = useCallback(
        (placeId: string) => favorites.has(placeId),
        [favorites],
    );

    const findPlace = useCallback(
        (placeId: string) =>
            route?.places[placeId] ??
            favoritePlaces.find((place) => place.id === placeId),
        [route, favoritePlaces],
    );

    useEffect(() => {
        if (USE_MOCKS) {
            const seeded = ["hermitage", "kazanKremlin", "olympicPark"];
            setFavorites(new Set(seeded));
            setFavoritePlaces(
                seeded.map((id) => MOCK_ROUTE.places[id]).filter(Boolean),
            );
            return;
        }

        void refreshTrips();
        void refreshFavorites();
    }, [refreshTrips, refreshFavorites]);

    // Restore the last opened trip after a reload.
    useEffect(() => {
        if (USE_MOCKS || routeState !== "idle" || !activeTripId) return;
        void openTrip(activeTripId);
    }, [activeTripId, openTrip, routeState]);

    const value = useMemo(
        () => ({
            draft,
            updateDraft,
            replaceDraft,
            toggleInterest,
            setPace,
            setAdults,
            setChildren,
            resetDraft,
            activeTripId,
            activeTripDraft,
            route,
            routeState,
            routeError,
            openTrip,
            adoptRoute,
            trips,
            tripsState,
            refreshTrips,
            removeTrip,
            favorites,
            favoritePlaces,
            toggleFavorite,
            isFavorite,
            findPlace,
        }),
        [
            draft,
            updateDraft,
            replaceDraft,
            toggleInterest,
            setPace,
            setAdults,
            setChildren,
            resetDraft,
            activeTripId,
            activeTripDraft,
            route,
            routeState,
            routeError,
            openTrip,
            adoptRoute,
            trips,
            tripsState,
            refreshTrips,
            removeTrip,
            favorites,
            favoritePlaces,
            toggleFavorite,
            isFavorite,
            findPlace,
        ],
    );

    return (
        <TripPlannerContext.Provider value={value}>
            {children}
        </TripPlannerContext.Provider>
    );
}
