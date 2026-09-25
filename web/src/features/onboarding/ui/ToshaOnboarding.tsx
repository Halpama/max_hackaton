import {
    useCallback,
    useEffect,
    useId,
    useLayoutEffect,
    useMemo,
    useRef,
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

const EMPTY_STEPS: OnboardingStep[] = [];

type Hole = {
    top: number;
    left: number;
    width: number;
    height: number;
    radius: number;
};

const RECT_PAD = 8;
const CIRCLE_PAD = 6;
const PANEL_FALLBACK_H = 300;
const PANEL_GAP = 18;
const VIEW_PAD = 12;

function targetIds(target: string | string[] | undefined): string[] {
    if (!target) return [];
    return Array.isArray(target) ? target : [target];
}

function queryTourNodes(ids: string[]): HTMLElement[] {
    if (typeof document === "undefined") return [];
    const nodes: HTMLElement[] = [];
    for (const id of ids) {
        const node = document.querySelector(
            `[data-tour="${id}"]`,
        ) as HTMLElement | null;
        if (node) nodes.push(node);
    }
    return nodes;
}

function findScrollParent(node: HTMLElement): HTMLElement | null {
    let current: HTMLElement | null = node.parentElement;
    while (current && current !== document.body) {
        const style = getComputedStyle(current);
        const overflowY = style.overflowY;
        if (
            (overflowY === "auto" ||
                overflowY === "scroll" ||
                overflowY === "overlay") &&
            current.scrollHeight > current.clientHeight + 4
        ) {
            return current;
        }
        current = current.parentElement;
    }
    return document.scrollingElement instanceof HTMLElement
        ? document.scrollingElement
        : null;
}

function measureHoleFromNodes(nodes: HTMLElement[]): Hole | null {
    if (nodes.length === 0) return null;

    if (nodes.length === 1) {
        const node = nodes[0];
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
            height: Math.min(
                window.innerHeight - 16,
                rect.height + RECT_PAD * 2,
            ),
            radius: 14,
        };
    }

    let top = Infinity;
    let left = Infinity;
    let right = -Infinity;
    let bottom = -Infinity;
    for (const node of nodes) {
        const rect = node.getBoundingClientRect();
        if (rect.width < 4 || rect.height < 4) continue;
        top = Math.min(top, rect.top);
        left = Math.min(left, rect.left);
        right = Math.max(right, rect.right);
        bottom = Math.max(bottom, rect.bottom);
    }
    if (!Number.isFinite(top)) return null;

    return {
        top: Math.max(8, top - RECT_PAD),
        left: Math.max(8, left - RECT_PAD),
        width: Math.min(window.innerWidth - 16, right - left + RECT_PAD * 2),
        height: Math.min(window.innerHeight - 16, bottom - top + RECT_PAD * 2),
        radius: 16,
    };
}

function measureTarget(target: string | string[] | undefined): Hole | null {
    return measureHoleFromNodes(queryTourNodes(targetIds(target)));
}

/** Scroll the spotlight target so the tour panel has room on the preferred side. */
function scrollTargetForPanel(
    target: string | string[] | undefined,
    prefer: "above" | "below",
    panelH: number,
) {
    const nodes = queryTourNodes(targetIds(target));
    if (nodes.length === 0) return;

    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    const top = first.getBoundingClientRect().top;
    const bottom = last.getBoundingClientRect().bottom;
    const safeBottom = VIEW_PAD;

    let delta = 0;
    if (prefer === "below") {
        const limit =
            window.innerHeight - panelH - PANEL_GAP - safeBottom;
        if (bottom > limit) delta = bottom - limit;
    } else {
        const limit = panelH + PANEL_GAP + VIEW_PAD;
        if (top < limit) delta = top - limit;
    }

    if (Math.abs(delta) < 6) return;

    // Tour locks body overflow — unlock briefly so the page can move.
    const body = document.body;
    const html = document.documentElement;
    const prevBody = body.style.overflow;
    const prevHtml = html.style.overflow;
    body.style.overflow = "";
    html.style.overflow = "";

    const scroller = findScrollParent(first);
    if (scroller) {
        scroller.scrollBy({ top: delta, behavior: "auto" });
    } else {
        window.scrollBy({ top: delta, behavior: "auto" });
    }

    body.style.overflow = prevBody;
    html.style.overflow = prevHtml;
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
    const forceTour = query.mode === "force" ? query.tour : null;
    const skipAll = query.mode === "skip";

    const [forcedTour, setForcedTour] = useState<TourId | null>(() => forceTour);
    const [hole, setHole] = useState<Hole | null>(null);
    const [poseReady, setPoseReady] = useState(false);
    const [panelH, setPanelH] = useState(PANEL_FALLBACK_H);
    const [dismissed, setDismissed] = useState<Partial<Record<TourId, boolean>>>(
        {},
    );
    const panelRef = useRef<HTMLDivElement | null>(null);

    const inferredTour = skipAll
        ? null
        : inferTourFromPath(location.pathname, location.search, routeReady);
    // Keep a React state copy so Skip always re-renders: create tour often has
    // forcedTour=null and stepIndex=0, so those setters alone were no-ops.
    const autoTour =
        inferredTour && dismissed[inferredTour] ? null : inferredTour;

    const activeTour: TourId | null = skipAll ? null : (forcedTour ?? autoTour);

    // Reset step index during render when the tour identity changes. Doing this
    // only in useEffect left one frame with the previous tour's stepIndex — if
    // that was the last home step (5) and create also has 6 steps, the create
    // tour opened on its final card so «Далее» called finish() immediately.
    const [stepTour, setStepTour] = useState<TourId | null>(activeTour);
    const [stepIndex, setStepIndex] = useState(0);
    if (activeTour !== stepTour) {
        setStepTour(activeTour);
        setStepIndex(0);
    }

    const steps = activeTour ? TOUR_STEPS[activeTour] : EMPTY_STEPS;
    const step = steps[stepIndex] ?? steps[0];
    const isLast = steps.length > 0 && stepIndex >= steps.length - 1;
    const onStepPage = step ? stepMatchesPath(step, location.pathname) : false;

    useEffect(() => {
        if (forceTour) {
            resetTour(forceTour);
            setDismissed((prev) => ({ ...prev, [forceTour]: false }));
            setForcedTour(forceTour);
            setStepIndex(0);
            if (
                forceTour === "home" &&
                location.pathname !== "/" &&
                location.pathname !== ROUTES.home
            ) {
                navigate(`${ROUTES.home}?onboarding=home`, { replace: true });
            } else if (
                forceTour === "create" &&
                location.pathname !== ROUTES.newTrip
            ) {
                navigate(`${ROUTES.newTrip}?onboarding=create`, {
                    replace: true,
                });
            } else if (
                forceTour === "prefs" &&
                location.pathname !== ROUTES.preferences
            ) {
                navigate(`${ROUTES.preferences}?onboarding=prefs`, {
                    replace: true,
                });
            } else if (
                forceTour === "route" &&
                location.pathname !== ROUTES.route
            ) {
                navigate(`${ROUTES.route}?onboarding=route`, { replace: true });
            }
            return;
        }
        if (skipAll) setForcedTour(null);
    }, [forceTour, skipAll, location.pathname, navigate]);

    // If the user navigates mid-tour (new-trip → preferences), snap to the
    // first step that belongs on the current page.
    useEffect(() => {
        if (!activeTour || steps.length === 0) return;
        const current = steps[stepIndex];
        if (current && stepMatchesPath(current, location.pathname)) return;
        const nextIndex = steps.findIndex((item) =>
            stepMatchesPath(item, location.pathname),
        );
        if (nextIndex >= 0 && nextIndex !== stepIndex) setStepIndex(nextIndex);
    }, [activeTour, location.pathname, stepIndex, steps]);

    const finish = useCallback(
        (skipped: boolean) => {
            if (activeTour) {
                markTourDone(activeTour, skipped);
                setDismissed((prev) => ({ ...prev, [activeTour]: true }));
            }
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
            setDismissed((prev) => ({ ...prev, [next]: false }));
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

        const preferBubble =
            step.bubble === "above" || step.bubble === "below"
                ? step.bubble
                : "below";

        const refresh = () => {
            if (!onStepPage) {
                setHole(null);
                return;
            }
            setHole(measureTarget(step.target));
        };

        if (onStepPage && step.target) {
            // Pick the side with more room before scrolling.
            const preview = measureTarget(step.target);
            let prefer: "above" | "below" = preferBubble;
            if (preview) {
                const spaceAbove = preview.top - VIEW_PAD;
                const spaceBelow =
                    window.innerHeight -
                    (preview.top + preview.height) -
                    VIEW_PAD;
                if (
                    prefer === "below" &&
                    spaceBelow < panelH &&
                    spaceAbove >= spaceBelow
                ) {
                    prefer = "above";
                } else if (
                    prefer === "above" &&
                    spaceAbove < panelH &&
                    spaceBelow > spaceAbove
                ) {
                    prefer = "below";
                }
            }
            scrollTargetForPanel(step.target, prefer, panelH);
        }

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
    }, [activeTour, step, onStepPage, panelH]);

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
            target: undefined as string | string[] | undefined,
            bubble: "center" as const,
        };
    }, [step, onStepPage]);

    // Fade the mascot in only when the pose asset changes — not on panel
    // resize (that used to flip poseReady off while cached onLoad never re-fired).
    useLayoutEffect(() => {
        if (!display?.pose) {
            setPoseReady(false);
            return;
        }
        setPoseReady(false);
        const src = TOSHA_POSES[display.pose];
        const probe = new Image();
        let cancelled = false;
        const mark = () => {
            if (!cancelled) setPoseReady(true);
        };
        probe.onload = mark;
        probe.onerror = mark;
        probe.src = src;
        if (probe.complete) mark();
        return () => {
            cancelled = true;
        };
    }, [display?.pose]);

    useLayoutEffect(() => {
        const node = panelRef.current;
        if (!node || typeof ResizeObserver === "undefined") return;
        const measure = () => {
            const next = Math.ceil(node.getBoundingClientRect().height);
            if (next > 0) setPanelH(next);
        };
        measure();
        const ro = new ResizeObserver(measure);
        ro.observe(node);
        return () => ro.disconnect();
    }, [activeTour, stepIndex, display?.title, display?.text]);

    const bubbleStyle = useMemo(() => {
        if (!display?.target || !hole) return undefined;

        const height = panelH || PANEL_FALLBACK_H;
        const safeTop = VIEW_PAD;
        const safeBottom = VIEW_PAD;
        const spaceAbove = hole.top - safeTop;
        const spaceBelow =
            window.innerHeight - (hole.top + hole.height) - safeBottom;

        let prefer: "above" | "below" =
            display.bubble === "above" || display.bubble === "below"
                ? display.bubble
                : hole.top > window.innerHeight * 0.45
                  ? "above"
                  : "below";

        if (prefer === "below" && spaceBelow < height && spaceAbove >= spaceBelow) {
            prefer = "above";
        } else if (
            prefer === "above" &&
            spaceAbove < height &&
            spaceBelow > spaceAbove
        ) {
            prefer = "below";
        }

        const side = "16px";
        if (prefer === "above") {
            const naturalBottom = window.innerHeight - hole.top + PANEL_GAP;
            const maxBottom = window.innerHeight - safeTop - height;
            const bottom = Math.min(
                Math.max(safeBottom, naturalBottom),
                Math.max(safeBottom, maxBottom),
            );
            return {
                bottom: `${bottom}px`,
                left: side,
                right: side,
            } as const;
        }

        const naturalTop = hole.top + hole.height + PANEL_GAP;
        const maxTop = window.innerHeight - safeBottom - height;
        const top = Math.min(Math.max(safeTop, naturalTop), Math.max(safeTop, maxTop));
        return {
            top: `${top}px`,
            left: side,
            right: side,
        } as const;
    }, [hole, display, panelH]);

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
                ref={panelRef}
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
                                onClick={(event) => {
                                    event.preventDefault();
                                    event.stopPropagation();
                                    finish(true);
                                }}
                            >
                                Пропустить
                            </button>
                            {onStepPage ? (
                                <button
                                    type="button"
                                    className={styles.next}
                                    onClick={(event) => {
                                        event.preventDefault();
                                        event.stopPropagation();
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
