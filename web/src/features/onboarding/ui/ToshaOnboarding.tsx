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
import {
    markOnboardingDone,
    readOnboardingDone,
    resetOnboarding,
    resolveOnboardingQuery,
} from "../lib/storage";
import {
    ONBOARDING_STEPS,
    TOSHA_POSES,
} from "../model/steps";
import styles from "./ToshaOnboarding.module.css";

type Hole = { top: number; left: number; width: number; height: number };

const PAD = 10;
const RADIUS = 18;

function measureTarget(tourId: string | undefined): Hole | null {
    if (!tourId || typeof document === "undefined") return null;
    const node = document.querySelector(
        `[data-tour="${tourId}"]`,
    ) as HTMLElement | null;
    if (!node) return null;
    const rect = node.getBoundingClientRect();
    if (rect.width < 4 || rect.height < 4) return null;
    return {
        top: Math.max(8, rect.top - PAD),
        left: Math.max(8, rect.left - PAD),
        width: Math.min(window.innerWidth - 16, rect.width + PAD * 2),
        height: Math.min(window.innerHeight - 16, rect.height + PAD * 2),
    };
}

function stripOnboardingParam(search: string) {
    const params = new URLSearchParams(search);
    if (!params.has("onboarding")) return null;
    params.delete("onboarding");
    const next = params.toString();
    return next ? `?${next}` : "";
}

export function ToshaOnboarding() {
    const location = useLocation();
    const navigate = useNavigate();
    const titleId = useId();
    const queryMode = resolveOnboardingQuery(location.search);

    const [active, setActive] = useState(() => {
        if (queryMode === "skip") return false;
        if (queryMode === "force") return true;
        return !readOnboardingDone();
    });
    const [stepIndex, setStepIndex] = useState(0);
    const [hole, setHole] = useState<Hole | null>(null);
    const [poseReady, setPoseReady] = useState(false);

    const step = ONBOARDING_STEPS[stepIndex] ?? ONBOARDING_STEPS[0];
    const isLast = stepIndex >= ONBOARDING_STEPS.length - 1;

    const onHome =
        location.pathname === ROUTES.home || location.pathname === "/";

    const finish = useCallback(
        (skipped: boolean) => {
            markOnboardingDone(skipped);
            setActive(false);
            const cleaned = stripOnboardingParam(location.search);
            if (cleaned !== null) {
                navigate(
                    { pathname: location.pathname, search: cleaned },
                    { replace: true },
                );
            }
        },
        [location.pathname, location.search, navigate],
    );

    const replay = useCallback(() => {
        resetOnboarding();
        setStepIndex(0);
        setActive(true);
        if (location.pathname !== ROUTES.home && location.pathname !== "/") {
            navigate(`${ROUTES.home}?onboarding=1`);
            return;
        }
        const params = new URLSearchParams(location.search);
        if (params.get("onboarding") !== "1") {
            params.set("onboarding", "1");
            const query = params.toString();
            navigate(
                { pathname: ROUTES.home, search: query ? `?${query}` : "" },
                { replace: true },
            );
        }
    }, [location.pathname, location.search, navigate]);

    useEffect(() => {
        if (queryMode === "force") {
            resetOnboarding();
            setStepIndex(0);
            setActive(true);
            if (!onHome) {
                navigate(`${ROUTES.home}?onboarding=1`, { replace: true });
            }
        } else if (queryMode === "skip") {
            setActive(false);
        }
    }, [queryMode, onHome, navigate]);

    useEffect(() => {
        const onReplay = () => replay();
        window.addEventListener("tosha:replay-onboarding", onReplay);
        return () =>
            window.removeEventListener("tosha:replay-onboarding", onReplay);
    }, [replay]);

    useLayoutEffect(() => {
        if (!active) return;
        setPoseReady(false);
        const refresh = () => setHole(measureTarget(step.target));
        refresh();
        const raf = requestAnimationFrame(refresh);
        window.addEventListener("resize", refresh);
        window.addEventListener("scroll", refresh, true);
        return () => {
            cancelAnimationFrame(raf);
            window.removeEventListener("resize", refresh);
            window.removeEventListener("scroll", refresh, true);
        };
    }, [active, step]);

    useEffect(() => {
        if (!active) return;
        const prev = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        return () => {
            document.body.style.overflow = prev;
        };
    }, [active]);

    const bubbleStyle = useMemo(() => {
        if (!step.target || !hole) return undefined;
        const prefer =
            step.bubble === "above" || step.bubble === "below"
                ? step.bubble
                : hole.top > window.innerHeight * 0.45
                  ? "above"
                  : "below";
        if (prefer === "above") {
            return {
                bottom: `${window.innerHeight - hole.top + 16}px`,
                left: "16px",
                right: "16px",
            } as const;
        }
        return {
            top: `${hole.top + hole.height + 16}px`,
            left: "16px",
            right: "16px",
        } as const;
    }, [hole, step]);

    if (!active) {
        return IS_DEV ? <DevReplayChip onReplay={replay} /> : null;
    }

    if (!onHome) {
        return IS_DEV ? <DevReplayChip onReplay={replay} /> : null;
    }

    return createPortal(
        <div
            className={styles.root}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
        >
            <div
                className={styles.dim}
                data-plain={hole ? "false" : "true"}
                aria-hidden
            >
                {hole ? (
                    <div
                        className={styles.hole}
                        style={{
                            top: hole.top,
                            left: hole.left,
                            width: hole.width,
                            height: hole.height,
                            borderRadius: RADIUS,
                        }}
                    />
                ) : null}
            </div>

            {hole ? (
                <div
                    className={styles.ring}
                    style={{
                        top: hole.top,
                        left: hole.left,
                        width: hole.width,
                        height: hole.height,
                        borderRadius: RADIUS,
                    }}
                    aria-hidden
                />
            ) : null}

            <button
                type="button"
                className={styles.skip}
                onClick={() => finish(true)}
            >
                Пропустить
            </button>

            <div
                className={
                    step.target ? styles.panelAnchored : styles.panelCenter
                }
                style={bubbleStyle}
            >
                <div className={styles.mascotWrap} data-pose={step.pose}>
                    <img
                        key={step.pose}
                        className={`${styles.mascot} ${poseReady ? styles.mascotIn : ""}`}
                        src={TOSHA_POSES[step.pose]}
                        alt=""
                        draggable={false}
                        onLoad={() => setPoseReady(true)}
                    />
                </div>

                <div className={styles.bubble}>
                    <p className={styles.kicker}>Тоша · гид</p>
                    <h2 id={titleId} className={styles.title}>
                        {step.title}
                    </h2>
                    <p className={styles.text}>{step.text}</p>

                    <div className={styles.footer}>
                        <div
                            className={styles.dots}
                            aria-label={`Шаг ${stepIndex + 1} из ${ONBOARDING_STEPS.length}`}
                        >
                            {ONBOARDING_STEPS.map((item, index) => (
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
                            {step.cta ?? (isLast ? "Начать" : "Дальше")}
                        </button>
                    </div>
                </div>
            </div>
        </div>,
        document.body,
    );
}

function DevReplayChip({ onReplay }: { onReplay: () => void }) {
    return (
        <button
            type="button"
            className={styles.devChip}
            onClick={onReplay}
            title="Сбросить и показать онбординг Тоши"
        >
            Тоша · demo
        </button>
    );
}
