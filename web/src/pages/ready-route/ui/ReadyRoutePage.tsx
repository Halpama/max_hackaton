import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ROUTES } from "@/shared/config";
import {
    ActivityCard,
    BudgetPanel,
    CalendarIcon,
    CityGuidePanel,
    CompassIcon,
    DayRouteMap,
    DayTabs,
    DayWeatherBadge,
    LoadingView,
    PackingPanel,
    PersonIcon,
    Screen,
    StatusView,
    TripActionsMenu,
    TransitHint,
    WarningIcon,
    parseTripTab,
    placeNavState,
    useTripLocalState,
    useTripPlanner,
} from "@/features/trip-planner";
import styles from "@/features/trip-planner/ui/shared/screens.module.css";

const ABOUT_TAB_ID = "about";

export function ReadyRoutePage() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const {
        route,
        routeState,
        routeError,
        activeTripId,
        activeTripDraft,
        openTrip,
        removeTrip,
        resetDraft,
    } = useTripPlanner();
    const startNewTrip = () => {
        resetDraft();
        navigate(ROUTES.newTrip);
    };
    const [actionsOpen, setActionsOpen] = useState(false);

    const requestedTripId = searchParams.get("tripId");
    const requestedDayId = searchParams.get("day");
    const mainTab = parseTripTab(searchParams.get("tab"));
    const [activeDayId, setActiveDayId] = useState(requestedDayId ?? "");

    useEffect(() => {
        if (requestedTripId && requestedTripId !== activeTripId) {
            void openTrip(requestedTripId);
        }
    }, [requestedTripId, activeTripId, openTrip]);

    useEffect(() => {
        if (!route) return;
        if (requestedDayId === ABOUT_TAB_ID) {
            setActiveDayId(ABOUT_TAB_ID);
            return;
        }
        if (
            requestedDayId &&
            route.days.some((item) => item.id === requestedDayId)
        ) {
            setActiveDayId(requestedDayId);
            return;
        }
        if (activeDayId === ABOUT_TAB_ID) return;
        if (
            !activeDayId ||
            !route.days.some((item) => item.id === activeDayId)
        ) {
            setActiveDayId(route.days[0]?.id ?? ABOUT_TAB_ID);
        }
    }, [route, requestedDayId, activeDayId]);

    const selectDay = (dayId: string) => {
        setActiveDayId(dayId);
        const next = new URLSearchParams(searchParams);
        next.set("day", dayId);
        if (activeTripId) next.set("tripId", activeTripId);
        setSearchParams(next, { replace: true });
    };

    const showingAbout = activeDayId === ABOUT_TAB_ID;

    const day = useMemo(() => {
        if (!route || showingAbout) return undefined;
        return (
            route.days.find((item) => item.id === activeDayId) ?? route.days[0]
        );
    }, [activeDayId, route, showingAbout]);

    const dayPlaces = useMemo(() => {
        if (!route || !day) return [];
        return day.activities
            .map((activity) => route.places[activity.placeId])
            .filter((place): place is NonNullable<typeof place> =>
                Boolean(place),
            );
    }, [day, route]);

    const dayLegModes = useMemo(
        () => (day?.transits ?? []).map((leg) => leg?.mode),
        [day],
    );

    const dayTabItems = useMemo(() => {
        if (!route) return [];
        return [
            { id: ABOUT_TAB_ID, label: "О поездке" },
            ...route.days.map(({ id, label }) => ({ id, label })),
        ];
    }, [route]);

    const tripId = activeTripId ?? "";
    const plannedBudget = Math.max(0, activeTripDraft?.budget ?? 0);

    const {
        packing,
        updatePacking,
        ledger,
        addLedgerEntry,
        removeLedgerEntry,
        remaining,
        spent,
        toppedUp,
        createId,
        todayIso,
    } = useTripLocalState(tripId, plannedBudget);

    if (!route) {
        if (routeState === "loading" || routeState === "idle") {
            return (
                <Screen>
                    <LoadingView title="Загружаем маршрут…" />
                </Screen>
            );
        }

        return (
            <Screen>
                <StatusView
                    tone="error"
                    icon={<WarningIcon />}
                    title="Маршрут недоступен"
                    text={
                        routeError ??
                        "Создайте новую поездку, чтобы увидеть маршрут."
                    }
                    actionLabel="Новая поездка"
                    onAction={startNewTrip}
                    secondaryActionLabel="На главную"
                    onSecondaryAction={() => navigate(ROUTES.home)}
                />
            </Screen>
        );
    }

    const guide = route.cityGuide;

    return (
        <Screen flush>
            <div className={styles.summary} data-tour="route-header">
                <div className={styles.top}>
                    <h1 className={styles.city}>{route.city}</h1>
                    {activeTripId ? (
                        <TripActionsMenu
                            open={actionsOpen}
                            onToggle={() => setActionsOpen((value) => !value)}
                            onClose={() => setActionsOpen(false)}
                            onEdit={() => {
                                setActionsOpen(false);
                                navigate(
                                    `${ROUTES.newTrip}?tripId=${activeTripId}`,
                                );
                            }}
                            onDelete={() => {
                                setActionsOpen(false);
                                if (
                                    window.confirm(
                                        `Удалить маршрут «${route.city}»?`,
                                    )
                                ) {
                                    void removeTrip(activeTripId).then(() =>
                                        navigate(ROUTES.home),
                                    );
                                }
                            }}
                        />
                    ) : null}
                </div>
                <p className={styles.meta}>
                    <span className={styles.metaItem}>
                        <CalendarIcon />
                        {route.dateLabel}
                    </span>
                    <span className={styles.metaDot} />
                    <span className={styles.metaItem}>
                        <PersonIcon />
                        {route.travelersLabel}
                    </span>
                </p>
            </div>

            {mainTab === "route" ? (
                <div key="route" className={styles.panel}>
                    <div className={styles.dayControls} data-tour="route-days">
                        <DayTabs
                            days={dayTabItems}
                            activeId={
                                showingAbout
                                    ? ABOUT_TAB_ID
                                    : (day?.id ?? ABOUT_TAB_ID)
                            }
                            onChange={selectDay}
                        />
                        {!showingAbout && day ? (
                            <DayWeatherBadge key={day.id} day={day} />
                        ) : null}
                    </div>

                    {showingAbout ? (
                        guide ? (
                            <CityGuidePanel city={route.city} guide={guide} />
                        ) : (
                            <StatusView
                                icon={<CompassIcon />}
                                title="Пока без обзора города"
                                text="Соберите маршрут ещё раз — подтянем краткую справку о городе."
                                actionLabel="Новая поездка"
                                onAction={startNewTrip}
                            />
                        )
                    ) : day && day.activities.length > 0 ? (
                        <>
                            <div
                                className={`${styles.mapWrap} ${styles.mapReveal}`}
                                data-tour="route-map"
                            >
                                <DayRouteMap
                                    places={dayPlaces}
                                    legModes={dayLegModes}
                                />
                            </div>

                            <div className={styles.list} key={day.id}>
                                {day.activities.map((activity, index) => {
                                    const fromPlace =
                                        route.places[activity.placeId];
                                    const toPlace =
                                        route.places[
                                            day.activities[index + 1]?.placeId
                                        ];
                                    const transit = day.transits[index];

                                    return (
                                        <div
                                            key={activity.id}
                                            className={styles.listItem}
                                            style={{
                                                animationDelay: `${index * 90}ms`,
                                            }}
                                        >
                                            <ActivityCard
                                                activity={activity}
                                                categoryKind={
                                                    fromPlace?.categoryKind
                                                }
                                                category={fromPlace?.category}
                                                onClick={() =>
                                                    navigate(
                                                        ROUTES.place(
                                                            activity.placeId,
                                                        ),
                                                        {
                                                            state: placeNavState(
                                                                "trip",
                                                                {
                                                                    tripId,
                                                                    dayId: day.id,
                                                                },
                                                            ),
                                                        },
                                                    )
                                                }
                                            />
                                            {transit && fromPlace && toPlace ? (
                                                <TransitHint
                                                    leg={transit}
                                                    from={fromPlace.coordinates}
                                                    to={toPlace.coordinates}
                                                />
                                            ) : null}
                                        </div>
                                    );
                                })}
                            </div>
                        </>
                    ) : (
                        <StatusView
                            icon={<CompassIcon />}
                            title="В этом дне пока пусто"
                            text="Попробуйте создать поездку заново с другими интересами."
                            actionLabel="Новая поездка"
                            onAction={startNewTrip}
                            secondaryActionLabel="На главную"
                            onSecondaryAction={() => navigate(ROUTES.home)}
                        />
                    )}
                </div>
            ) : null}

            {mainTab === "packing" ? (
                <div key="packing" className={styles.panel}>
                    <PackingPanel
                        blocks={packing}
                        onChange={updatePacking}
                        createId={createId}
                    />
                </div>
            ) : null}

            {mainTab === "budget" ? (
                <div key="budget" className={styles.panel}>
                    <BudgetPanel
                        plannedBudget={plannedBudget}
                        remaining={remaining}
                        spent={spent}
                        toppedUp={toppedUp}
                        ledger={ledger}
                        todayIso={todayIso}
                        onAdd={addLedgerEntry}
                        onRemove={removeLedgerEntry}
                    />
                </div>
            ) : null}
        </Screen>
    );
}
