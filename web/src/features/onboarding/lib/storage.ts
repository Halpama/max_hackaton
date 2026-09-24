/** Persist whether Tosha's first-run tour was finished or skipped. */

export const ONBOARDING_STORAGE_KEY = "tp-tosha-onboarding-v1";

export type OnboardingRecord = {
    done: boolean;
    skipped?: boolean;
    at?: string;
};

export function readOnboardingDone(): boolean {
    try {
        const raw = localStorage.getItem(ONBOARDING_STORAGE_KEY);
        if (!raw) return false;
        const parsed = JSON.parse(raw) as OnboardingRecord;
        return Boolean(parsed?.done);
    } catch {
        return false;
    }
}

export function markOnboardingDone(skipped = false) {
    try {
        const payload: OnboardingRecord = {
            done: true,
            skipped,
            at: new Date().toISOString(),
        };
        localStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify(payload));
    } catch {
        // Private mode — tour may reappear next visit.
    }
}

export function resetOnboarding() {
    try {
        localStorage.removeItem(ONBOARDING_STORAGE_KEY);
    } catch {
        // ignore
    }
}

/** Dev / QA helpers via query string. */
export function resolveOnboardingQuery(
    search: string,
): "force" | "skip" | "auto" {
    const params = new URLSearchParams(search);
    const raw = params.get("onboarding");
    if (raw === "1" || raw === "true" || raw === "replay" || raw === "force") {
        return "force";
    }
    if (raw === "0" || raw === "false" || raw === "off") {
        return "skip";
    }
    return "auto";
}
