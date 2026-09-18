import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'
import styles from './trip.module.css'

export function SectionLabel({ children }: { children: ReactNode }) {
  return <p className={styles.label}>{children}</p>
}

export function Section({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <section className={styles.section}>
      <SectionLabel>{label}</SectionLabel>
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
