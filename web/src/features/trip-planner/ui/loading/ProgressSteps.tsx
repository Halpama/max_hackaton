import { CheckIcon } from '../shared/icons-sprite'
import styles from './ProgressSteps.module.css'

interface ProgressStepsProps {
  steps: readonly string[]
  activeIndex: number
}

export function ProgressSteps({ steps, activeIndex }: ProgressStepsProps) {
  return (
    <div className={styles.card}>
      <div className={styles.list}>
        {steps.map((step, index) => {
          const done = index < activeIndex
          const active = index === activeIndex
          const labelClass = done
            ? styles.labelDone
            : active
              ? styles.labelActive
              : styles.label
          const markerClass = done
            ? styles.markerDone
            : active
              ? styles.markerActive
              : styles.marker

          return (
            <div key={step}>
              <div className={styles.step}>
                <span className={markerClass}>
                  {done ? <CheckIcon /> : active ? <span className={styles.spinner} /> : null}
                </span>
                <p className={labelClass}>{step}</p>
              </div>
              {index < steps.length - 1 ? (
                <div className={done ? styles.connectorDone : styles.connector} />
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
