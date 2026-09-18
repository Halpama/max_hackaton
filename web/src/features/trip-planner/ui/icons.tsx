import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

export function SearchIcon(props: IconProps) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.8" />
      <path d="M20 20l-3.2-3.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function CalendarIcon(props: IconProps) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <rect x="3.5" y="5.5" width="17" height="15" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3.5 10.5h17M8 3.5v4M16 3.5v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function RubleIcon(props: IconProps) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M8 4.5h6.2a3.8 3.8 0 0 1 0 7.6H8V4.5zm0 7.6h4.5M8 4.5V19.5M7 14.5h6.5M7 17.5h6.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function PersonIcon(props: IconProps) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <circle cx="12" cy="8" r="3.25" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M5.5 18.5c1.4-2.8 3.7-4.2 6.5-4.2s5.1 1.4 6.5 4.2"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function SparklesIcon(props: IconProps) {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M12 2.8l1.85 6.35L20.2 11l-6.35 1.85L12 19.2l-1.85-6.35L3.8 11l6.35-1.85L12 2.8z"
        fill="currentColor"
      />
      <path
        d="M19.1 3.6l.58 1.95 1.95.58-1.95.58-.58 1.95-.58-1.95-1.95-.58 1.95-.58.58-1.95z"
        fill="currentColor"
      />
    </svg>
  )
}

export function StarIcon(props: IconProps) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.8 6.4 20.2l1.1-6.2L3 9.6l6.2-.9L12 3z" />
    </svg>
  )
}

export function MuseumIcon(props: IconProps) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M4 10h16v9H4v-9z" stroke="currentColor" strokeWidth="1.7" />
      <path d="M3 10l9-6 9 6" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M8 19v-6M12 19v-6M16 19v-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  )
}

export function PinIcon(props: IconProps) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M12 21s6-5.2 6-10a6 6 0 1 0-12 0c0 4.8 6 10 6 10z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <circle cx="12" cy="11" r="2.2" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  )
}

export function FoodIcon(props: IconProps) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M8 3v8M6 3v4a2 2 0 0 0 4 0V3M8 11v10" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M16 3v18M16 3c2.2 0 4 1.8 4 5v3h-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  )
}

export function WalkIcon(props: IconProps) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" {...props}>
      <circle cx="13.5" cy="5" r="2" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M8 21l2.2-6.2L7 12l3-4 3.2 2.4 2.3-1.2L18 11"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function HeartIcon({ filled = false, ...props }: IconProps & { filled?: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M12 20s-7-4.4-7-9.2A3.8 3.8 0 0 1 12 7.5a3.8 3.8 0 0 1 7 3.3C19 15.6 12 20 12 20z"
        fill={filled ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function CheckIcon(props: IconProps) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M5 12.5l5 5L19 7"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function MinusIcon(props: IconProps) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M6 12h12" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

export function PlusIcon(props: IconProps) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M12 6v12M6 12h12" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

export function MapIcon(props: IconProps) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M9 4.5l-5 2v13l5-2 6 2 5-2v-13l-5 2-6-2z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path d="M9 4.5v13M15 6.5v13" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  )
}

export function BagIcon(props: IconProps) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M6.5 9.5h11l-.7 9.2a2 2 0 0 1-2 1.8H9.2a2 2 0 0 1-2-1.8L6.5 9.5z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M9 9.5V7.8A3 3 0 0 1 12 4.8 3 3 0 0 1 15 7.8v1.7"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function TextBlockIcon(props: IconProps) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M5 7h14M5 12h10M5 17h12"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function BulletListIcon(props: IconProps) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <circle cx="6" cy="7" r="1.4" fill="currentColor" />
      <circle cx="6" cy="12" r="1.4" fill="currentColor" />
      <circle cx="6" cy="17" r="1.4" fill="currentColor" />
      <path
        d="M10.5 7h8.5M10.5 12h8.5M10.5 17h8.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function ChecklistIcon(props: IconProps) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
      <rect
        x="4"
        y="5.5"
        width="5"
        height="5"
        rx="1.2"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <path
        d="M5.2 8l1.3 1.3L9.2 6.6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12.5 8h7.5M4.5 16.5h15"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}
