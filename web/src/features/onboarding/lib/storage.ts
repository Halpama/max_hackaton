/** Persist Tosha tour completion per stage. */

export type TourId = "home" | "create" | "prefs" | "route";

export type OnboardingRecord = {
    done: boolean;
    skipped?: boolean;
    at?: string;
};

const TOUR_KEYS: Record<TourId, string> = {
    home: "tp-tosha-onboarding-home-v1",
    create: "tp-tosha-onboarding-create-v1",
    prefs: "tp-tosha-onboarding-prefs-v1",
    route: "tp-tosha-onboarding-route-v1",
};

/** Pre-multi-tour key — migrate into `home`. */
const LEGACY_HOME_KEY = "tp-tosha-onboarding-v1";

function readRecord(key: string): OnboardingRecord | null {
    try {
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        return JSON.parse(raw) as OnboardingRecord;
    } catch {
        return null;
    }
}

function writeRecord(key: string, skipped: boolean) {
    try {
        const payload: OnboardingRecord = {
            done: true,
            skipped,
            at: new Date().toISOString(),
        };
        localStorage.setItem(key, JSON.stringify(payload));
    } catch {
        // Private mode — tour may reappear next visit.
    }
}

export function readTourDone(tour: TourId): boolean {
    if (tour === "home") {
        const legacy = readRecord(LEGACY_HOME_KEY);
        if (legacy?.done) {
            writeRecord(TOUR_KEYS.home, Boolean(legacy.skipped));
            try {
                localStorage.removeItem(LEGACY_HOME_KEY);
            } catch {
                // ignore
            }
            return true;
        }
    }
    return Boolean(readRecord(TOUR_KEYS[tour])?.done);
}

export function markTourDone(tour: TourId, skipped = false) {
    writeRecord(TOUR_KEYS[tour], skipped);
}

export function resetTour(tour: TourId) {
    try {
        localStorage.removeItem(TOUR_KEYS[tour]);
        if (tour === "home") localStorage.removeItem(LEGACY_HOME_KEY);
    } catch {
        // ignore
    }
}

export function resetAllTours() {
    (Object.keys(TOUR_KEYS) as TourId[]).forEach(resetTour);
}

/** @deprecated use readTourDone('home') */
export function readOnboardingDone() {
    return readTourDone("home");
}

/** @deprecated use markTourDone('home') */
export function markOnboardingDone(skipped = false) {
    markTourDone("home", skipped);
}

/** @deprecated use resetTour / resetAllTours */
export function resetOnboarding() {
    resetAllTours();
}

export const ONBOARDING_STORAGE_KEY = TOUR_KEYS.home;

export type OnboardingQuery =
    | { mode: "auto" }
    | { mode: "skip" }
    | { mode: "force"; tour: TourId };

/** Dev / QA helpers via query string. */
export function resolveOnboardingQuery(search: string): OnboardingQuery {
    const params = new URLSearchParams(search);
    const raw = params.get("onboarding");
    if (!raw) return { mode: "auto" };
    if (raw === "0" || raw === "false" || raw === "off") {
        return { mode: "skip" };
    }
    if (raw === "create" || raw === "prefs" || raw === "route" || raw === "home") {
        return { mode: "force", tour: raw };
    }
    if (raw === "1" || raw === "true" || raw === "replay" || raw === "force") {
        return { mode: "force", tour: "home" };
    }
    return { mode: "auto" };
}
