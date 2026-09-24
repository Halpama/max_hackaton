import { resetOnboarding } from "./storage";

/** Imperative replay for help modal / console / dev chip. */
export function requestToshaOnboardingReplay() {
    resetOnboarding();
    window.dispatchEvent(new Event("tosha:replay-onboarding"));
}
