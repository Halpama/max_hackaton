import { useEffect, useLayoutEffect, useRef } from "react";
import { MoreVerticalIcon, PencilIcon, TrashIcon } from "./icons";
import styles from "./TripActionsMenu.module.css";

/** Keeps the panel away from the viewport edge when it has to be clamped. */
const VIEWPORT_GAP = 12;

interface TripActionsMenuProps {
    open: boolean;
    onToggle: () => void;
    onClose: () => void;
    onEdit: () => void;
    onDelete: () => void;
    align?: "start" | "end";
}

export function TripActionsMenu({
    open,
    onToggle,
    onClose,
    onEdit,
    onDelete,
    align = "end",
}: TripActionsMenuProps) {
    const rootRef = useRef<HTMLDivElement>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        const onPointerDown = (event: PointerEvent) => {
            if (!rootRef.current?.contains(event.target as Node)) onClose();
        };
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") onClose();
        };
        document.addEventListener("pointerdown", onPointerDown);
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.removeEventListener("pointerdown", onPointerDown);
            document.removeEventListener("keydown", onKeyDown);
        };
    }, [open, onClose]);

    // Anchoring the panel to the trigger overflows on the left column of the
    // home grid, so it is shifted into the viewport before the first paint.
    useLayoutEffect(() => {
        if (!open) return;

        const position = () => {
            const root = rootRef.current;
            const menu = menuRef.current;
            if (!root || !menu) return;

            const rect = root.getBoundingClientRect();
            const width = menu.offsetWidth;
            const viewport = document.documentElement.clientWidth;
            const preferred = align === "end" ? rect.right - width : rect.left;
            const min = VIEWPORT_GAP;
            const max = Math.max(min, viewport - width - VIEWPORT_GAP);

            menu.style.left = `${Math.min(Math.max(preferred, min), max) - rect.left}px`;
            menu.style.right = "auto";
        };

        position();
        window.addEventListener("resize", position);
        window.addEventListener("scroll", position, true);
        return () => {
            window.removeEventListener("resize", position);
            window.removeEventListener("scroll", position, true);
        };
    }, [open, align]);

    return (
        <div ref={rootRef} className={styles.root} data-align={align}>
            <button
                type="button"
                className={styles.trigger}
                aria-label="Действия с маршрутом"
                aria-haspopup="menu"
                aria-expanded={open}
                onClick={(event) => {
                    event.stopPropagation();
                    onToggle();
                }}
            >
                <MoreVerticalIcon />
            </button>
            <div
                ref={menuRef}
                className={`${styles.menu} ${open ? styles.menuOpen : ""}`}
                role="menu"
                aria-hidden={!open}
            >
                <button
                    type="button"
                    role="menuitem"
                    className={styles.item}
                    onClick={(event) => {
                        event.stopPropagation();
                        onEdit();
                    }}
                >
                    <PencilIcon />
                    Изменить параметры
                </button>
                <button
                    type="button"
                    role="menuitem"
                    className={`${styles.item} ${styles.delete}`}
                    onClick={(event) => {
                        event.stopPropagation();
                        onDelete();
                    }}
                >
                    <TrashIcon />
                    Удалить маршрут
                </button>
            </div>
        </div>
    );
}
