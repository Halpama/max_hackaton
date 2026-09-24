import {
    useCallback,
    useEffect,
    useId,
    useLayoutEffect,
    useMemo,
    useState,
} from "react";
import { createPortal } from "react-dom";
import { useLocation, useNavigate } from "react-router-dom";
import { IS_DEV, ROUTES } from "@/shared/config";
import { useTripPlanner } from "@/features/trip-planner";
import {
    markTourDone,
    readTourDone,
    resetAllTours,
    resetTour,
    resolveOnboardingQuery,
    type TourId,
} from "../lib/storage";
import {
    stepMatchesPath,
    TOUR_STEPS,
    TOSHA_POSES,
    tourHomePath,
    type OnboardingStep,
} from "../model/steps";
import styles from "./ToshaOnboarding.module.css";

type Hole = {
    top: number;
    left: number;
    width: number;
    height: number;
    radius: number;
};

const RECT_PAD = 8;
const CIRCLE_PAD = 6;

function measureTarget(tourId: string | undefined): Hole | null {
    if (!tourId || typeof document === "undefined") return null;
    const node = document.querySelector(
        `[data-tour="${tourId}"]`,
    ) as HTMLElement | null;
    if (!node) return null;

    const rect = node.getBoundingClientRect();
    if (rect.width < 4 || rect.height < 4) return null;

    const shapeAttr = node.getAttribute("data-tour-shape");
    const nearlySquare = Math.abs(rect.width - rect.height) < 10;
    const isCircle =
        shapeAttr === "circle" ||
        (shapeAttr !== "rect" && nearlySquare && rect.width <= 72);

    if (isCircle) {
        const size = Math.max(rect.width, rect.height) + CIRCLE_PAD * 2;
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        return {
            top: cy - size / 2,
            left: cx - size / 2,
            width: size,
            height: size,
            radius: size / 2,
        };
    }

    return {
        top: Math.max(8, rect.top - RECT_PAD),
        left: Math.max(8, rect.left - RECT_PAD),
        width: Math.min(window.innerWidth - 16, rect.width + RECT_PAD * 2),
        height: Math.min(window.innerHeight - 16, rect.height + RECT_PAD * 2),
        radius: 14,
    };
}

function stripOnboardingParam(search: string) {
    const params = new URLSearchParams(search);
    if (!params.has("onboarding")) return null;
    params.delete("onboarding");
    const next = params.toString();
    return next ? `?${next}` : "";
}

function inferTourFromPath(
    pathname: string,
    search: string,
    routeReady: boolean,
): TourId | null {
    const params = new URLSearchParams(search);
    if (pathname === ROUTES.home || pathname === "/") {
        if (!readTourDone("home")) return "home";
        return null;
    }
    if (pathname === ROUTES.newTrip || pathname.startsWith(`${ROUTES.newTrip}/`)) {
        if (params.get("tripId")) return null;
        if (!readTourDone("create")) return "create";
        return null;
    }
    if (pathname === ROUTES.preferences) {
        if (!readTourDone("prefs")) return "prefs";
        return null;
    }
    if (pathname === ROUTES.route && routeReady) {
        if (!readTourDone("route")) return "route";
        return null;
    }
    return null;
}

function bridgeCopy(step: OnboardingStep): { title: string; text: string } {
    if (step.paths?.includes("/preferences")) {
        return {
            title: "Следующий экран",
            text: "Нажми «Далее» внизу формы — там расскажу про интересы и темп.",
        };
    }
    if (step.paths?.includes("/trips/new")) {
        return {
            title: "Вернёмся к форме",
            text: "Этот шаг на экране новой поездки. Открой создание маршрута, и продолжим.",
        };
    }
    if (step.paths?.includes("/route")) {
        return {
            title: "Нужен готовый маршрут",
            text: "Открой собранную поездку — покажу дни, карту и нижнее меню.",
        };
    }
    return {
        title: step.title,
        text: step.text,
    };
}

export function ToshaOnboarding() {
    const location = useLocation();
    const navigate = useNavigate();
    const titleId = useId();
    const { route, routeState } = useTripPlanner();
    const routeReady = routeState === "ready" && Boolean(route);
    const query = resolveOnboardingQuery(location.search);

    const [forcedTour, setForcedTour] = useState<TourId | null>(() =>
        query.mode === "force" ? query.tour : null,
    );
    const [stepIndex, setStepIndex] = useState(0);
    const [hole, setHole] = useState<Hole | null>(null);
    const [poseReady, setPoseReady] = useState(false);

    const autoTour =
        query.mode === "skip"
            ? null
            : inferTourFromPath(location.pathname, location.search, routeReady);

    const activeTour: TourId | null =
        query.mode === "skip" ? null : (forcedTour ?? autoTour);

    const steps = activeTour ? TOUR_STEPS[activeTour] : [];
    const step = steps[stepIndex] ?? steps[0];
    const isLast = stepIndex >= steps.length - 1;
    const onStepPage = step ? stepMatchesPath(step, location.pathname) : false;

    useEffect(() => {
        if (query.mode === "force") {
            resetTour(query.tour);
            setForcedTour(query.tour);
            setStepIndex(0);
            if (
                query.tour === "home" &&
                location.pathname !== "/" &&
                location.pathname !== ROUTES.home
            ) {
                navigate(`${ROUTES.home}?onboarding=home`, { replace: true });
            } else if (
                query.tour === "create" &&
                location.pathname !== ROUTES.newTrip
            ) {
                navigate(`${ROUTES.newTrip}?onboarding=create`, {
                    replace: true,
                });
            } else if (
                query.tour === "prefs" &&
                location.pathname !== ROUTES.preferences
            ) {
                navigate(`${ROUTES.preferences}?onboarding=prefs`, {
                    replace: true,
                });
            } else if (
                query.tour === "route" &&
                location.pathname !== ROUTES.route
            ) {
                navigate(`${ROUTES.route}?onboarding=route`, { replace: true });
            }
        } else if (query.mode === "skip") {
            setForcedTour(null);
        }
    }, [query, location.pathname, navigate]);

    useEffect(() => {
        setStepIndex(0);
    }, [activeTour]);

    // If the user navigates mid-tour (new-trip → preferences), snap to the
    // first step that belongs on the current page.
    useEffect(() => {
        if (!activeTour || steps.length === 0) return;
        const current = steps[stepIndex];
        if (current && stepMatchesPath(current, location.pathname)) return;
        const nextIndex = steps.findIndex((item) =>
            stepMatchesPath(item, location.pathname),
        );
        if (nextIndex >= 0) setStepIndex(nextIndex);
    }, [activeTour, location.pathname, stepIndex, steps]);

    const finish = useCallback(
        (skipped: boolean) => {
            if (activeTour) markTourDone(activeTour, skipped);
            setForcedTour(null);
            setStepIndex(0);
            const cleaned = stripOnboardingParam(location.search);
            if (cleaned !== null) {
                navigate(
                    { pathname: location.pathname, search: cleaned },
                    { replace: true },
                );
            }
        },
        [activeTour, location.pathname, location.search, navigate],
    );

    const replay = useCallback(
        (tour?: TourId) => {
            const next =
                tour ??
                inferTourFromPath(
                    location.pathname,
                    location.search,
                    routeReady,
                ) ??
                "home";
            resetTour(next);
            setForcedTour(next);
            setStepIndex(0);
            const params = new URLSearchParams(location.search);
            params.set("onboarding", next);
            const targetPath = tourHomePath(next);
            navigate(
                {
                    pathname: targetPath,
                    search: `?${params.toString()}`,
                },
                { replace: true },
            );
        },
        [location.pathname, location.search, navigate, routeReady],
    );

    useEffect(() => {
        const onReplay = (event: Event) => {
            const detail = (event as CustomEvent<TourId | undefined>).detail;
            replay(detail);
        };
        window.addEventListener("tosha:replay-onboarding", onReplay);
        return () =>
            window.removeEventListener("tosha:replay-onboarding", onReplay);
    }, [replay]);

    useLayoutEffect(() => {
        if (!activeTour || !step) return;
        setPoseReady(false);
        const refresh = () => {
            if (!onStepPage) {
                setHole(null);
                return;
            }
            setHole(measureTarget(step.target));
        };
        refresh();
        const raf = requestAnimationFrame(refresh);
        const timer = window.setTimeout(refresh, 80);
        window.addEventListener("resize", refresh);
        window.addEventListener("scroll", refresh, true);
        return () => {
            cancelAnimationFrame(raf);
            window.clearTimeout(timer);
            window.removeEventListener("resize", refresh);
            window.removeEventListener("scroll", refresh, true);
        };
    }, [activeTour, step, onStepPage]);

    useEffect(() => {
        if (!activeTour) return;
        const prev = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        return () => {
            document.body.style.overflow = prev;
        };
    }, [activeTour]);

    const display = useMemo(() => {
        if (!step) return null;
        if (onStepPage) {
            return {
                title: step.title,
                text: step.text,
                pose: step.pose,
                cta: step.cta,
                target: step.target,
                bubble: step.bubble,
            };
        }
        const bridge = bridgeCopy(step);
        return {
            title: bridge.title,
            text: bridge.text,
            pose: step.pose,
            cta: undefined as string | undefined,
            target: undefined as string | undefined,
            bubble: "center" as const,
        };
    }, [step, onStepPage]);

    const bubbleStyle = useMemo(() => {
        if (!display?.target || !hole) return undefined;
        const prefer =
            display.bubble === "above" || display.bubble === "below"
                ? display.bubble
                : hole.top > window.innerHeight * 0.45
                  ? "above"
                  : "below";
        if (prefer === "above") {
            return {
                bottom: `${window.innerHeight - hole.top + 18}px`,
                left: "16px",
                right: "16px",
            } as const;
        }
        return {
            top: `${hole.top + hole.height + 18}px`,
            left: "16px",
            right: "16px",
        } as const;
    }, [hole, display]);

    if (!activeTour || !step || !display) {
        return IS_DEV ? (
            <DevReplayChip
                onReplay={() => replay()}
                onResetAll={() => {
                    resetAllTours();
                    replay("home");
                }}
            />
        ) : null;
    }

    const showHole = Boolean(display.target && hole);

    return createPortal(
        <div
            className={styles.root}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
        >
            <div
                className={styles.dim}
                data-plain={showHole ? "false" : "true"}
                aria-hidden
            >
                {showHole && hole ? (
                    <div
                        className={styles.hole}
                        style={{
                            top: hole.top,
                            left: hole.left,
                            width: hole.width,
                            height: hole.height,
                            borderRadius: hole.radius,
                        }}
                    />
                ) : null}
            </div>

            {showHole && hole ? (
                <div
                    className={styles.ring}
                    style={{
                        top: hole.top,
                        left: hole.left,
                        width: hole.width,
                        height: hole.height,
                        borderRadius: hole.radius,
                    }}
                    aria-hidden
                />
            ) : null}

            <div
                className={
                    display.target && hole
                        ? styles.panelAnchored
                        : styles.panelCenter
                }
                style={bubbleStyle}
            >
                <div className={styles.mascotWrap}>
                    <img
                        key={display.pose}
                        className={`${styles.mascot} ${poseReady ? styles.mascotIn : ""}`}
                        src={TOSHA_POSES[display.pose]}
                        alt=""
                        draggable={false}
                        onLoad={() => setPoseReady(true)}
                    />
                </div>

                <div className={styles.bubble}>
                    <p className={styles.kicker}>Тоша</p>
                    <h2 id={titleId} className={styles.title}>
                        {display.title}
                    </h2>
                    <p className={styles.text}>{display.text}</p>

                    <div className={styles.footer}>
                        <div
                            className={styles.dots}
                            aria-label={`Шаг ${stepIndex + 1} из ${steps.length}`}
                        >
                            {steps.map((item, index) => (
                                <span
                                    key={item.id}
                                    className={
                                        index === stepIndex
                                            ? styles.dotActive
                                            : index < stepIndex
                                              ? styles.dotDone
                                              : styles.dot
                                    }
                                />
                            ))}
                        </div>
                        <div className={styles.actions}>
                            <button
                                type="button"
                                className={styles.skipText}
                                onClick={() => finish(true)}
                            >
                                Пропустить
                            </button>
                            {onStepPage ? (
                                <button
                                    type="button"
                                    className={styles.next}
                                    onClick={() => {
                                        if (isLast) {
                                            finish(false);
                                            return;
                                        }
                                        setStepIndex((value) => value + 1);
                                    }}
                                >
                                    {display.cta ??
                                        (isLast ? "Готово" : "Дальше")}
                                </button>
                            ) : null}
                        </div>
                    </div>
                </div>
            </div>
        </div>,
        document.body,
    );
}

function DevReplayChip({
    onReplay,
    onResetAll,
}: {
    onReplay: () => void;
    onResetAll: () => void;
}) {
    return (
        <div className={styles.devCluster}>
            <button
                type="button"
                className={styles.devChip}
                onClick={onReplay}
                title="Повторить тур для текущего экрана"
            >
                Тоша · demo
            </button>
            <button
                type="button"
                className={styles.devChipGhost}
                onClick={onResetAll}
                title="Сбросить все туры и открыть домашний"
            >
                reset all
            </button>
        </div>
    );
}
