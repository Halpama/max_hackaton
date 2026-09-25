import { useEffect, useId } from "react";
import { createPortal } from "react-dom";
import styles from "./DeleteTripModal.module.css";

export function DeleteTripModal({
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
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        window.addEventListener("keydown", onKey);
        return () => {
            document.body.style.overflow = previousOverflow;
            window.removeEventListener("keydown", onKey);
        };
    }, [busy, onCancel]);

    return createPortal(
        <div className={styles.root} role="presentation" onClick={onCancel}>
            <div
                className={styles.modal}
                role="dialog"
                aria-modal="true"
                aria-labelledby={titleId}
                onClick={(event) => event.stopPropagation()}
            >
                <h2 id={titleId} className={styles.title}>
                    Удалить поездку?
                </h2>
                <p className={styles.text}>
                    Маршрут «{city}» исчезнет из списка. Избранные места и
                    данные поездки останутся в системе.
                </p>
                <div className={styles.actions}>
                    <button
                        type="button"
                        className={styles.cancel}
                        disabled={busy}
                        onClick={onCancel}
                    >
                        Отмена
                    </button>
                    <button
                        type="button"
                        className={styles.delete}
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