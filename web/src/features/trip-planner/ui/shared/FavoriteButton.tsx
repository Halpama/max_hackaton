import type { ButtonHTMLAttributes } from 'react'
import { HeartIcon } from './icons'
import styles from './trip.module.css'

interface FavoriteButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active: boolean
}

export function FavoriteButton({ active, ...props }: FavoriteButtonProps) {
  return (
    <button
      type="button"
      className={active ? styles.favoriteBtnActive : styles.favoriteBtn}
      aria-pressed={active}
      {...props}
    >
      <HeartIcon filled={active} />
      {active ? 'В избранном' : 'В избранное'}
    </button>
  )
}
