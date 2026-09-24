import { resetTour, resetAllTours, type TourId } from "./storage";

/** Imperative replay for help modal / console / dev chip. */
export function requestToshaOnboardingReplay(tour: TourId = "home") {
    resetTour(tour);
    window.dispatchEvent(
        new CustomEvent<TourId>("tosha:replay-onboarding", { detail: tour }),
    );
}

export function requestToshaOnboardingResetAll() {
    resetAllTours();
    window.dispatchEvent(
        new CustomEvent<TourId>("tosha:replay-onboarding", { detail: "home" }),
    );
}
