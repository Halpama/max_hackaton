import React from 'react'

interface SkeletonProps {
  className?: string
  width?: string | number
  height?: string | number
  circle?: boolean
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  width = '100%',
  height = '16px',
  circle = false,
}) => {
  const style: React.CSSProperties = {
    width,
    height,
    borderRadius: circle ? '9999px' : '4px',
    background: 'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0) 100%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s ease-in-out infinite',
  }

  return <div className={className} style={style} />
}

/* Ключевые кадры для анимации мерцания */
const styleSheet = document.styleSheets[0]
if (styleSheet) {
  try {
    styleSheet.insertRule(`
      @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
      }
    `, styleSheet.cssRules.length)
  } catch {
    // Игнорируем ошибку, если правило уже существует
  }
}

export default Skeleton