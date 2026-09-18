import type { ReactNode } from 'react'
import { MinusIcon, PlusIcon } from './icons'
import styles from './Stepper.module.css'

interface StepperProps {
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
  label: string
  icon?: ReactNode
}

export function Stepper({
  value,
  onChange,
  min = 1,
  max = 10,
  label,
  icon,
}: StepperProps) {
  return (
    <div className={styles.row}>
      <div className={styles.meta}>
        {icon ? <span className={styles.icon}>{icon}</span> : null}
        <span className={styles.label}>{label}</span>
      </div>
      <div className={styles.controls}>
        <button
          type="button"
          className={styles.btn}
          aria-label="Уменьшить"
          disabled={value <= min}
          onClick={() => onChange(value - 1)}
        >
          <MinusIcon />
        </button>
        <span className={styles.value}>{value}</span>
        <button
          type="button"
          className={styles.btn}
          aria-label="Увеличить"
          disabled={value >= max}
          onClick={() => onChange(value + 1)}
        >
          <PlusIcon />
        </button>
      </div>
    </div>
  )
}
