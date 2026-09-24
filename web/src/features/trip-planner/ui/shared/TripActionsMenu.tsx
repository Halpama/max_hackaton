import { useEffect, useRef } from "react";
import { MoreVerticalIcon, PencilIcon, TrashIcon } from "./icons";
import styles from "./TripActionsMenu.module.css";

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
