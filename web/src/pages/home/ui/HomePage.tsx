import {
    useEffect,
    useId,
    useMemo,
    useRef,
    useState,
    type PointerEvent,
} from "react";
import { createPortal } from "react-dom";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Input, Icon16SearchOutline } from "@maxhub/max-ui";
import { ROUTES } from "@/shared/config";
import {
    CompassIcon,
    HeartIcon,
    InfoIcon,
    Screen,
    SoftImage,
    StarIcon,
    StatusView,
    TripActionsMenu,
    WarningIcon,
    placeNavState,
    useTripPlanner,
    type Place,
    type TripSummary,
} from "@/features/trip-planner";
import {
    knownCityImage,
    resolveCityImage,
} from "@/features/trip-planner/lib/cityImage";
import { formatPlaceTitle } from "@/features/trip-planner/lib/format";
import tripStyles from "@/features/trip-planner/ui/shared/trip.module.css";
import styles from "@/features/trip-planner/ui/home/home.module.css";

export function HomePage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const {
        trips,
        tripsState,
        refreshTrips,
        favoritePlaces,
        openTrip,
        removeTrip,
        toggleFavorite,
        resetDraft,
    } = useTripPlanner();
    const tab = searchParams.get("tab") === "favorites" ? "favorites" : "trips";
    const [query, setQuery] = useState("");
    const [city, setCity] = useState("Все");
    const [helpOpen, setHelpOpen] = useState(false);

    const cities = useMemo(() => {
        const unique = [...new Set(favoritePlaces.map((place) => place.city))];
        return ["Все", ...unique];
    }, [favoritePlaces]);

    const filteredFavorites = useMemo(() => {
        const normalized = query.trim().toLowerCase();
        return favoritePlaces.filter((place) => {
            const matchesCity = city === "Все" || place.city === city;
            const matchesQuery =
                !normalized ||
                place.title.toLowerCase().includes(normalized) ||
                place.category.toLowerCase().includes(normalized) ||
                place.city.toLowerCase().includes(normalized);
            return matchesCity && matchesQuery;
        });
    }, [city, favoritePlaces, query]);

    const handleOpenTrip = (tripId: string) => {
        void openTrip(tripId);
        navigate(`${ROUTES.route}?tripId=${tripId}`);
    };

    return (
        <Screen>
            {tab === "trips" ? (
                <TripsTab
                    key="trips"
                    trips={trips}
                    state={tripsState}
                    onRetry={() => void refreshTrips()}
                    onCreate={() => {
                        resetDraft();
                        navigate(ROUTES.newTrip);
                    }}
                    onOpenTrip={handleOpenTrip}
                    onRemoveTrip={removeTrip}
                    onHelp={() => setHelpOpen(true)}
                />
            ) : (
                <FavoritesTab
                    key="favorites"
                    query={query}
                    onQueryChange={setQuery}
                    cities={cities}
                    city={city}
                    onCityChange={setCity}
                    places={filteredFavorites}
                    hasAny={favoritePlaces.length > 0}
                    onOpenPlace={(placeId) =>
                        navigate(ROUTES.place(placeId), {
                            state: placeNavState("favorites"),
                        })
                    }
                    onToggleFavorite={toggleFavorite}
                    onHelp={() => setHelpOpen(true)}
                />
            )}
            {helpOpen ? (
                <HowItWorksModal onClose={() => setHelpOpen(false)} />
            ) : null}
        </Screen>
    );
}

function BrandTitleRow({
    title,
    onHelp,
}: {
    title: string;
    onHelp: () => void;
}) {
    return (
        <div className={styles.titleRow}>
            <img src="/logo.svg" alt="2РИСТ" className={styles.brandLogo} />
            <h1 className={tripStyles.title}>{title}</h1>
            <button
                type="button"
                className={styles.helpBtn}
                aria-label="Как это работает"
                onClick={onHelp}
            >
                <InfoIcon />
            </button>
        </div>
    );
}

function TripsTab({
    trips,
    state,
    onRetry,
    onCreate,
    onOpenTrip,
    onRemoveTrip,
    onHelp,
}: {
    trips: TripSummary[];
    state: "idle" | "loading" | "ready" | "error";
    onRetry: () => void;
    onCreate: () => void;
    onOpenTrip: (tripId: string) => void;
    onRemoveTrip: (tripId: string) => Promise<void>;
    onHelp: () => void;
}) {
    const navigate = useNavigate();
    const [pendingDelete, setPendingDelete] = useState<TripSummary | null>(
        null,
    );
    const [deleting, setDeleting] = useState(false);
    const [openActionsId, setOpenActionsId] = useState<string | null>(null);
    const longPressRef = useRef<number | null>(null);
    const longPressedRef = useRef(false);

    const clearLongPress = () => {
        if (longPressRef.current !== null) {
            window.clearTimeout(longPressRef.current);
            longPressRef.current = null;
        }
    };

    const startLongPress =
        (trip: TripSummary) => (event: PointerEvent<HTMLDivElement>) => {
            if (event.pointerType === "mouse") return;
            clearLongPress();
            longPressRef.current = window.setTimeout(() => {
                longPressedRef.current = true;
                setOpenActionsId(trip.id);
            }, 520);
        };

    const confirmDelete = async () => {
        if (!pendingDelete || deleting) return;
        setDeleting(true);
        try {
            await onRemoveTrip(pendingDelete.id);
            setPendingDelete(null);
        } catch {
            // List is refreshed by the provider on failure.
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className={styles.stack}>
            <BrandTitleRow title="Мои поездки" onHelp={onHelp} />

            {state === "error" ? (
                <StatusView
                    tone="error"
                    icon={<WarningIcon />}
                    title="Не удалось загрузить поездки"
                    text="Не получилось связаться с сервером. Попробуйте ещё раз чуть позже."
                    actionLabel="Повторить"
                    onAction={onRetry}
                />
            ) : trips.length === 0 &&
              (state === "loading" || state === "idle") ? (
                <div className={styles.gridSkeleton} aria-hidden>
                    {Array.from({ length: 4 }, (_, index) => (
                        <div key={index} className={styles.skeletonTile} />
                    ))}
                </div>
            ) : trips.length === 0 ? (
                <StatusView
                    icon={<CompassIcon />}
                    title="Поездок пока нет"
                    text="Создайте первую — ИИ подберёт места и соберёт маршрут по дням."
                    actionLabel="Новая поездка"
                    onAction={onCreate}
                />
            ) : (
                <div className={styles.grid}>
                    {trips.map((trip, index) => (
                        <div
                            key={trip.id}
                            className={styles.tile}
                            style={{ animationDelay: `${index * 60}ms` }}
                            onPointerDown={startLongPress(trip)}
                            onPointerUp={clearLongPress}
                            onPointerCancel={clearLongPress}
                            onPointerLeave={clearLongPress}
                            onContextMenu={(event) => event.preventDefault()}
                        >
                            <button
                                type="button"
                                className={styles.tileHit}
                                onClick={() => {
                                    clearLongPress();
                                    if (longPressedRef.current) {
                                        longPressedRef.current = false;
                                        return;
                                    }
                                    onOpenTrip(trip.id);
                                }}
                            >
                                <div className={styles.media}>
                                    <div className={styles.mediaFrame}>
                                        <TripCover city={trip.city} />
                                    </div>
                                    <span
                                        className={styles.mediaShade}
                                        aria-hidden
                                    />
                                    <span className={styles.badge}>
                                        <TripStatusBadge status={trip.status} />
                                    </span>
                                    <div className={styles.tileBody}>
                                        <p className={styles.tileTitle}>
                                            {trip.city}
                                        </p>
                                        <p className={styles.tileMeta}>
                                            {trip.dateLabel} ·{" "}
                                            {trip.travelersLabel}
                                        </p>
                                        <p className={styles.tileBudget}>
                                            {trip.budgetLabel}
                                        </p>
                                    </div>
                                </div>
                            </button>
                            <div
                                className={styles.tileActions}
                                onClick={(event) => event.stopPropagation()}
                            >
                                <TripActionsMenu
                                    open={openActionsId === trip.id}
                                    onToggle={() =>
                                        setOpenActionsId((value) =>
                                            value === trip.id ? null : trip.id,
                                        )
                                    }
                                    onClose={() => setOpenActionsId(null)}
                                    onEdit={() => {
                                        setOpenActionsId(null);
                                        navigate(
                                            `${ROUTES.newTrip}?tripId=${trip.id}`,
                                        );
                                    }}
                                    onDelete={() => {
                                        setOpenActionsId(null);
                                        setPendingDelete(trip);
                                    }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {pendingDelete ? (
                <DeleteTripModal
                    city={pendingDelete.city}
                    busy={deleting}
                    onCancel={() => {
                        if (!deleting) setPendingDelete(null);
                    }}
                    onConfirm={() => void confirmDelete()}
                />
            ) : null}
        </div>
    );
}

function DeleteTripModal({
    city,
    busy,
    onCancel,
    onConfirm,
}: {
    city: string;
    busy: boolean;
    onCancel: () => void;
    onConfirm: () => void;
}) {
    const titleId = useId();

    useEffect(() => {
        const onKey = (event: KeyboardEvent) => {
            if (event.key === "Escape" && !busy) onCancel();
        };
        const prev = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        window.addEventListener("keydown", onKey);
        return () => {
            document.body.style.overflow = prev;
            window.removeEventListener("keydown", onKey);
        };
    }, [busy, onCancel]);

    return createPortal(
        <div
            className={styles.confirmRoot}
            role="presentation"
            onClick={onCancel}
        >
            <div
                className={styles.confirmModal}
                role="dialog"
                aria-modal="true"
                aria-labelledby={titleId}
                onClick={(event) => event.stopPropagation()}
            >
                <h2 id={titleId} className={styles.confirmTitle}>
                    Удалить поездку?
                </h2>
                <p className={styles.confirmText}>
                    Маршрут «{city}» исчезнет из списка. Избранные места и
                    данные поездки останутся в системе.
                </p>
                <div className={styles.confirmActions}>
                    <button
                        type="button"
                        className={styles.confirmCancel}
                        disabled={busy}
                        onClick={onCancel}
                    >
                        Отмена
                    </button>
                    <button
                        type="button"
                        className={styles.confirmDelete}
                        disabled={busy}
                        onClick={onConfirm}
                    >
                        {busy ? "Удаляем…" : "Удалить"}
                    </button>
                </div>
            </div>
        </div>,
        document.body,
    );
}

function HowItWorksModal({ onClose }: { onClose: () => void }) {
    const titleId = useId();
    const dragRef = useRef<{
        startY: number;
        lastY: number;
        dragging: boolean;
    }>({
        startY: 0,
        lastY: 0,
        dragging: false,
    });
    const [dragY, setDragY] = useState(0);
    const [dragging, setDragging] = useState(false);

    useEffect(() => {
        const onKey = (event: KeyboardEvent) => {
            if (event.key === "Escape") onClose();
        };
        const prev = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        window.addEventListener("keydown", onKey);
        return () => {
            document.body.style.overflow = prev;
            window.removeEventListener("keydown", onKey);
        };
    }, [onClose]);

    const onHandlePointerDown = (event: PointerEvent<HTMLButtonElement>) => {
        event.currentTarget.setPointerCapture(event.pointerId);
        dragRef.current = {
            startY: event.clientY,
            lastY: event.clientY,
            dragging: true,
        };
        setDragging(true);
        setDragY(0);
    };

    const onHandlePointerMove = (event: PointerEvent<HTMLButtonElement>) => {
        if (!dragRef.current.dragging) return;
        const delta = Math.max(0, event.clientY - dragRef.current.startY);
        dragRef.current.lastY = event.clientY;
        setDragY(delta);
    };

    const finishDrag = () => {
        if (!dragRef.current.dragging) return;
        const delta = Math.max(
            0,
            dragRef.current.lastY - dragRef.current.startY,
        );
        dragRef.current.dragging = false;
        setDragging(false);
        if (delta > 80) {
            onClose();
            return;
        }
        setDragY(0);
    };

    const backdropOpacity = Math.max(0.12, 0.4 * (1 - dragY / 280));

    return createPortal(
        <div
            className={styles.helpRoot}
            role="presentation"
            style={{ background: `rgba(15, 23, 42, ${backdropOpacity})` }}
            onClick={onClose}
        >
            <div
                className={
                    dragging ? styles.helpModalDragging : styles.helpModal
                }
                role="dialog"
                aria-modal="true"
                aria-labelledby={titleId}
                style={{
                    transform: dragY ? `translateY(${dragY}px)` : undefined,
                }}
                onClick={(event) => event.stopPropagation()}
            >
                <button
                    type="button"
                    className={styles.helpHandle}
                    aria-label="Потяните вниз, чтобы закрыть"
                    onPointerDown={onHandlePointerDown}
                    onPointerMove={onHandlePointerMove}
                    onPointerUp={finishDrag}
                    onPointerCancel={finishDrag}
                />
                <h2 id={titleId} className={styles.helpTitle}>
                    Как это работает
                </h2>
                <ol className={styles.helpList}>
                    <li>
                        <strong>Новая поездка</strong> — город, даты, бюджет и
                        интересы.
                    </li>
                    <li>
                        <strong>ИИ собирает маршрут</strong> по дням: места,
                        время и дорога между ними.
                    </li>
                    <li>
                        <strong>Сборы и бюджет</strong> — чеклист вещей и учёт
                        трат в одной поездке.
                    </li>
                    <li>
                        <strong>Избранное</strong> — сохраняйте места из
                        маршрута, чтобы вернуться к ним позже.
                    </li>
                </ol>
                <button
                    type="button"
                    className={styles.helpClose}
                    onClick={onClose}
                >
                    Понятно
                </button>
            </div>
        </div>,
        document.body,
    );
}

function TripStatusBadge({ status }: { status: TripSummary["status"] }) {
    if (status === "ready") {
        return <span className={styles.statusReady}>Готов</span>;
    }
    if (status === "failed") {
        return <span className={styles.statusFailed}>Ошибка</span>;
    }
    if (status === "running") {
        return <span className={styles.statusRunning}>Строится…</span>;
    }
    return <span className={styles.statusDraft}>В очереди</span>;
}

function TripCover({ city }: { city: string }) {
    const [src, setSrc] = useState<string | null>(() => knownCityImage(city));
    const [failed, setFailed] = useState(false);
    const [resolving, setResolving] = useState(() => !knownCityImage(city));

    useEffect(() => {
        let cancelled = false;
        setFailed(false);
        const known = knownCityImage(city);
        if (known) {
            setSrc(known);
            setResolving(false);
            return;
        }
        setSrc(null);
        setResolving(true);
        void resolveCityImage(city).then((url) => {
            if (cancelled) return;
            setSrc(url);
            setResolving(false);
        });
        return () => {
            cancelled = true;
        };
    }, [city]);

    if (resolving && !src) {
        return <span className={styles.imageSkeleton} aria-hidden />;
    }

    if (!src || failed) {
        return (
            <div className={styles.coverFallback} aria-hidden>
                <span>{city.slice(0, 1).toUpperCase()}</span>
            </div>
        );
    }

    return (
        <SoftImage
            className={styles.coverImg}
            skeletonClassName={styles.coverSkeleton}
            src={src}
            alt=""
            loading="lazy"
            onError={() => setFailed(true)}
        />
    );
}

function FavoritesTab({
    query,
    onQueryChange,
    cities,
    city,
    onCityChange,
    places,
    hasAny,
    onOpenPlace,
    onToggleFavorite,
    onHelp,
}: {
    query: string;
    onQueryChange: (value: string) => void;
    cities: string[];
    city: string;
    onCityChange: (value: string) => void;
    places: Place[];
    hasAny: boolean;
    onOpenPlace: (placeId: string) => void;
    onToggleFavorite: (placeId: string) => void;
    onHelp: () => void;
}) {
    return (
        <div className={styles.stack}>
            <BrandTitleRow title="Избранное" onHelp={onHelp} />

            {!hasAny ? (
                <StatusView
                    icon={<HeartIcon />}
                    title="Здесь пока пусто"
                    text="Открывайте места в маршруте и добавляйте их в избранное — они появятся тут."
                />
            ) : (
                <>
                    <Input
                        mode="contrast"
                        size="large"
                        placeholder="Поиск по избранным"
                        value={query}
                        onChange={(event) => onQueryChange(event.target.value)}
                        iconBefore={<Icon16SearchOutline />}
                        withClearButton
                    />

                    <div className={styles.filters}>
                        {cities.map((item) => (
                            <button
                                key={item}
                                type="button"
                                className={
                                    item === city
                                        ? styles.chipActive
                                        : styles.chip
                                }
                                onClick={() => onCityChange(item)}
                            >
                                {item}
                            </button>
                        ))}
                    </div>

                    {places.length === 0 ? (
                        <p className={styles.empty}>Пока ничего не найдено</p>
                    ) : (
                        <div className={styles.grid}>
                            {places.map((place, index) => (
                                <div
                                    key={place.id}
                                    className={styles.tile}
                                    style={{
                                        animationDelay: `${index * 60}ms`,
                                    }}
                                >
                                    <button
                                        type="button"
                                        className={styles.tileHit}
                                        onClick={() => onOpenPlace(place.id)}
                                    >
                                        <div className={styles.media}>
                                            <div className={styles.mediaFrame}>
                                                <FavoriteThumb place={place} />
                                            </div>
                                            <span
                                                className={styles.mediaShade}
                                                aria-hidden
                                            />
                                            <span
                                                className={styles.ratingFloat}
                                            >
                                                <StarIcon />
                                                {place.rating}
                                            </span>
                                            <div className={styles.tileBody}>
                                                <p className={styles.tileTitle}>
                                                    {formatPlaceTitle(
                                                        place.title,
                                                    )}
                                                </p>
                                                <p className={styles.tileMeta}>
                                                    {place.city} ·{" "}
                                                    {shortCategory(
                                                        place.category,
                                                    )}
                                                </p>
                                            </div>
                                        </div>
                                    </button>
                                    <button
                                        type="button"
                                        className={styles.favToggle}
                                        aria-label="Убрать из избранного"
                                        aria-pressed
                                        onClick={(event) => {
                                            event.stopPropagation();
                                            onToggleFavorite(place.id);
                                        }}
                                    >
                                        <HeartIcon filled />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

function shortCategory(category: string) {
    const first = category.split(/[·,]/)[0]?.trim();
    return first && first.length <= 22 ? first : `${category.slice(0, 20)}…`;
}

function FavoriteThumb({ place }: { place: Place }) {
    const [failed, setFailed] = useState(false);

    if (failed || !place.imageUrl) {
        return (
            <div className={styles.coverFallback} aria-hidden>
                <span>{place.title.slice(0, 1).toUpperCase()}</span>
            </div>
        );
    }

    return (
        <SoftImage
            className={styles.coverImg}
            skeletonClassName={styles.coverSkeleton}
            src={place.imageUrl}
            alt=""
            loading="lazy"
            onError={() => setFailed(true)}
        />
    );
}
