import {
  useId,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from 'react'
import styles from './trip.module.css'

export function SectionLabel({ children }: { children: ReactNode }) {
  return <p className={styles.label}>{children}</p>
}

export function Section({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: ReactNode
}) {
  const hintId = useId()
  const [hintOpen, setHintOpen] = useState(false)

  return (
    <section className={styles.section}>
      <div className={styles.labelRow}>
        <SectionLabel>{label}</SectionLabel>
        {hint ? (
          <button
            type="button"
            className={hintOpen ? styles.hintBtnOpen : styles.hintBtn}
            aria-label="Подсказка"
            aria-expanded={hintOpen}
            aria-controls={hintId}
            title={hint}
            onClick={() => setHintOpen((open) => !open)}
          >
            ?
          </button>
        ) : null}
      </div>
      {hint ? (
        <div
          className={hintOpen ? styles.hintPanelOpen : styles.hintPanel}
          id={hintId}
          role="note"
          aria-hidden={!hintOpen}
        >
          <div className={styles.hintPanelInner}>
            <p className={styles.hintText}>{hint}</p>
          </div>
        </div>
      ) : null}
      {children}
    </section>
  )
}

export function TextField({
  icon,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { icon?: ReactNode }) {
  return (
    <label className={styles.field}>
      {icon ? <span className={styles.fieldIcon}>{icon}</span> : null}
      <input className={styles.fieldInput} {...props} />
    </label>
  )
}

export function PrimaryButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={styles.primaryBtn} {...props} />
}

export function SecondaryButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={styles.secondaryBtn} {...props} />
}
