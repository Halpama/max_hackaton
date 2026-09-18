import { Switch } from '@maxhub/max-ui'
import styles from './OptionCard.module.css'

interface OptionCardProps {
  title: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}

export function OptionCard({ title, description, checked, onChange }: OptionCardProps) {
  return (
    <label className={styles.card}>
      <div className={styles.copy}>
        <p className={styles.title}>{title}</p>
        <p className={styles.desc}>{description}</p>
      </div>
      <Switch
        checked={checked}
        onChange={(event) => onChange(event.currentTarget.checked)}
      />
    </label>
  )
}
