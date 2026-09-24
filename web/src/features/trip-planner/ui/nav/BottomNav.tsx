import {
    useLayoutEffect,
    useMemo,
    useRef,
    useState,
    type ReactNode,
} from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ROUTES } from "@/shared/config";
import {
    BagIcon,
    CloseIcon,
    HeartIcon,
    MapIcon,
    PlusIcon,
    RubleIcon,
} from "../shared/icons";
import { useTripPlanner } from "../../model/useTripPlanner";
import styles from "./BottomNav.module.css";

type NavContext = "home" | "trip";

type NavItem = {
    id: string;
    label: string;
    icon: ReactNode;
    emphasis?: boolean;
    onSelect: () => void;
    active: boolean;
};

const WIZARD_PREFIXES = [ROUTES.newTrip, ROUTES.preferences, ROUTES.loading];

export function shouldShowBottomNav(pathname: string): boolean {
    return !WIZARD_PREFIXES.some(
        (path) => pathname === path || pathname.startsWith(`${path}/`),
    );
}

function resolveContext(pathname: string, state: unknown): NavContext {
    if (pathname === ROUTES.route) return "trip";
    if (pathname.startsWith("/places/")) {
        return getPlaceNavFrom(state) === "favorites" ? "home" : "trip";
    }
    return "home";
}

export type PlaceNavFrom = "trip" | "favorites";

export type PlaceNavState = {
    navFrom: PlaceNavFrom;
    tripId?: string;
    dayId?: string;
};

export function placeNavState(
    from: PlaceNavFrom,
    extras?: { tripId?: string; dayId?: string },
): PlaceNavState {
    return {
        navFrom: from,
        tripId: extras?.tripId,
        dayId: extras?.dayId,
    };
}

function getPlaceNavFrom(state: unknown): PlaceNavFrom | null {
    if (!state || typeof state !== "object") return null;
    const navFrom = (state as { navFrom?: unknown }).navFrom;
    if (navFrom === "trip" || navFrom === "favorites") return navFrom;
    return null;
}

function readPlaceNavExtras(state: unknown): {
    tripId?: string;
    dayId?: string;
} {
    if (!state || typeof state !== "object") return {};
    const raw = state as { tripId?: unknown; dayId?: unknown };
    return {
        tripId: typeof raw.tripId === "string" ? raw.tripId : undefined,
        dayId: typeof raw.dayId === "string" ? raw.dayId : undefined,
    };
}

export function tripRoutePath(
    tripId?: string | null,
    dayId?: string | null,
): string {
    const params = new URLSearchParams();
    if (tripId) params.set("tripId", tripId);
    if (dayId) params.set("day", dayId);
    const query = params.toString();
    return query ? `${ROUTES.route}?${query}` : ROUTES.route;
}

export function BottomNav() {
    const navigate = useNavigate();
    const location = useLocation();
    const { resetDraft } = useTripPlanner();
    const [searchParams] = useSearchParams();
    const placeFrom = getPlaceNavFrom(location.state);
    const onPlace = location.pathname.startsWith("/places/");
    const context = resolveContext(location.pathname, location.state);
    const closeMode = onPlace && placeFrom !== "favorites";
    const activeTripFromQuery = searchParams.get("tripId");
    const homeTab =
        onPlace && placeFrom === "favorites"
            ? "favorites"
            : searchParams.get("tab") === "favorites"
              ? "favorites"
              : "trips";
    const tripTab = parseTripTab(searchParams.get("tab"));
    const tripActiveTab = closeMode ? "route" : tripTab;
    const dayFromQuery = searchParams.get("day");

    const tripHref = (tab?: TripNavTab) => {
        const params = new URLSearchParams();
        if (activeTripFromQuery) params.set("tripId", activeTripFromQuery);
        if (dayFromQuery) params.set("day", dayFromQuery);
        if (tab && tab !== "route") params.set("tab", tab);
        const query = params.toString();
        return query ? `${ROUTES.route}?${query}` : ROUTES.route;
    };

    const items = useMemo<NavItem[]>(() => {
        if (context === "trip") {
            return [
                {
                    id: "route",
                    label: "Маршрут",
                    icon: <MapIcon />,
                    active: tripActiveTab === "route",
                    onSelect: () => navigate(tripHref("route")),
                },
                {
                    id: "packing",
                    label: "Сборы",
                    icon: <BagIcon />,
                    active: tripActiveTab === "packing",
                    onSelect: () => navigate(tripHref("packing")),
                },
                {
                    id: "budget",
                    label: "Бюджет",
                    icon: <RubleIcon />,
                    active: tripActiveTab === "budget",
                    onSelect: () => navigate(tripHref("budget")),
                },
                {
                    id: "trips",
                    label: "Поездки",
                    icon: <TripsIcon />,
                    active: false,
                    onSelect: () => navigate(ROUTES.home),
                },
            ];
        }

        return [
            {
                id: "trips",
                label: "Поездки",
                icon: <TripsIcon />,
                active: homeTab === "trips",
                onSelect: () => navigate(ROUTES.home),
            },
            {
                id: "new",
                label: "Новая",
                icon: <PlusIcon />,
                emphasis: true,
                active: false,
                onSelect: () => {
                    resetDraft();
                    navigate(ROUTES.newTrip);
                },
            },
            {
                id: "favorites",
                label: "Избранное",
                icon: <HeartIcon filled={homeTab === "favorites"} />,
                active: homeTab === "favorites",
                onSelect: () => navigate(`${ROUTES.home}?tab=favorites`),
            },
        ];
    }, [
        context,
        homeTab,
        navigate,
        resetDraft,
        tripActiveTab,
        activeTripFromQuery,
        dayFromQuery,
    ]);

    const activeIndex = Math.max(
        0,
        items.findIndex((item) => item.active),
    );
    const hasActive = items.some((item) => item.active) && !closeMode;

    const shellRef = useRef<HTMLDivElement | null>(null);
    const listRef = useRef<HTMLDivElement | null>(null);
    const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);
    const wasCloseRef = useRef(closeMode);
    /** After X → tabs, hold the active pill until the shell finishes expanding. */
    const holdPillRef = useRef(false);
    const [pill, setPill] = useState({
        left: 0,
        top: 0,
        width: 0,
        height: 0,
        ready: false,
    });

    useLayoutEffect(() => {
        if (wasCloseRef.current && !closeMode) {
            holdPillRef.current = true;
        }
        if (closeMode) {
            holdPillRef.current = false;
        }
        wasCloseRef.current = closeMode;
    }, [closeMode]);

    useLayoutEffect(() => {
        if (closeMode || !hasActive) {
            setPill((prev) => (prev.ready ? { ...prev, ready: false } : prev));
            return;
        }

        const revealPill = () => {
            const button = itemRefs.current[activeIndex];
            if (!button) {
                setPill((prev) =>
                    prev.ready ? { ...prev, ready: false } : prev,
                );
                return;
            }

            const width = button.offsetWidth;
            const height = button.offsetHeight;
            if (width < 40 || height < 24) {
                setPill((prev) =>
                    prev.ready ? { ...prev, ready: false } : prev,
                );
                return;
            }

            setPill({
                left: button.offsetLeft,
                top: button.offsetTop,
                width,
                height,
                ready: !holdPillRef.current,
            });
        };

        const releasePill = () => {
            holdPillRef.current = false;
            revealPill();
            // One more frame after layout settles at full width.
            requestAnimationFrame(() => {
                const button = itemRefs.current[activeIndex];
                if (!button || button.offsetWidth < 40) return;
                setPill({
                    left: button.offsetLeft,
                    top: button.offsetTop,
                    width: button.offsetWidth,
                    height: button.offsetHeight,
                    ready: true,
                });
            });
        };

        setPill((prev) => (prev.ready ? { ...prev, ready: false } : prev));
        revealPill();

        const shell = shellRef.current;
        const list = listRef.current;
        const raf = requestAnimationFrame(() => {
            revealPill();
            requestAnimationFrame(revealPill);
        });

        const onTransitionEnd = (event: TransitionEvent) => {
            if (event.target !== shell) return;
            if (
                event.propertyName === "max-width" ||
                event.propertyName === "min-height" ||
                event.propertyName === "padding"
            ) {
                releasePill();
            }
        };
        shell?.addEventListener("transitionend", onTransitionEnd);

        // Fallback if transitionend doesn't fire (reduced motion / no morph).
        const timer = window.setTimeout(
            releasePill,
            holdPillRef.current ? 520 : 80,
        );

        const observer =
            typeof ResizeObserver !== "undefined" && list
                ? new ResizeObserver(() => {
                      if (!holdPillRef.current) revealPill();
                  })
                : null;
        if (list && observer) observer.observe(list);

        window.addEventListener("resize", revealPill);

        return () => {
            cancelAnimationFrame(raf);
            window.clearTimeout(timer);
            shell?.removeEventListener("transitionend", onTransitionEnd);
            observer?.disconnect();
            window.removeEventListener("resize", revealPill);
        };
    }, [activeIndex, hasActive, items, closeMode, context]);

    return (
        <nav
            className={styles.root}
            data-mode={closeMode ? "close" : "tabs"}
            aria-label="Основная навигация"
        >
            <div
                ref={shellRef}
                key={context}
                className={styles.shell}
                data-context={context}
                data-mode={closeMode ? "close" : "tabs"}
            >
                {!closeMode ? (
                    <div ref={listRef} className={styles.list} role="tablist">
                        <span
                            className={
                                pill.ready ? styles.pill : styles.pillHidden
                            }
                            style={{
                                width: pill.width,
                                height: pill.height,
                                transform: `translate(${pill.left}px, ${pill.top}px)`,
                            }}
                            aria-hidden
                        />
                        {items.map((item, index) => (
                            <button
                                key={item.id}
                                ref={(node) => {
                                    itemRefs.current[index] = node;
                                }}
                                type="button"
                                role="tab"
                                aria-selected={item.active}
                                aria-label={
                                    item.emphasis ? "Новая поездка" : item.label
                                }
                                data-tour={
                                    item.id === "favorites"
                                        ? "nav-favorites"
                                        : item.id === "trips"
                                          ? "nav-trips"
                                          : item.id === "packing"
                                            ? "nav-packing"
                                            : item.id === "budget"
                                              ? "nav-budget"
                                              : undefined
                                }
                                className={
                                    item.emphasis
                                        ? styles.emphasis
                                        : item.active
                                          ? styles.itemActive
                                          : styles.item
                                }
                                style={{
                                    animationDelay: `${40 + index * 45}ms`,
                                }}
                                onClick={item.onSelect}
                            >
                                {item.emphasis ? (
                                    <span
                                        className={styles.fab}
                                        data-tour="nav-new"
                                        data-tour-shape="circle"
                                        aria-hidden
                                    >
                                        {item.icon}
                                    </span>
                                ) : (
                                    <>
                                        <span
                                            className={styles.icon}
                                            aria-hidden
                                        >
                                            {item.icon}
                                        </span>
                                        <span className={styles.label}>
                                            {item.label}
                                        </span>
                                    </>
                                )}
                            </button>
                        ))}
                    </div>
                ) : (
                    <button
                        type="button"
                        className={styles.closeBtn}
                        aria-label="Закрыть"
                        onClick={() => {
                            const extras = readPlaceNavExtras(location.state);
                            navigate(
                                tripRoutePath(
                                    extras.tripId ?? activeTripFromQuery,
                                    extras.dayId,
                                ),
                            );
                        }}
                    >
                        <CloseIcon />
                    </button>
                )}
            </div>
        </nav>
    );
}

export type TripNavTab = "route" | "packing" | "budget";

export function parseTripTab(raw: string | null): TripNavTab {
    if (raw === "packing" || raw === "budget") return raw;
    return "route";
}

function TripsIcon() {
    return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
            <rect
                x="4.5"
                y="7.5"
                width="15"
                height="12"
                rx="3"
                stroke="currentColor"
                strokeWidth="1.8"
            />
            <path
                d="M9 7.5V6.2A2.2 2.2 0 0 1 11.2 4h1.6A2.2 2.2 0 0 1 15 6.2v1.3"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
            />
            <path d="M4.5 12.5h15" stroke="currentColor" strokeWidth="1.8" />
        </svg>
    );
}
