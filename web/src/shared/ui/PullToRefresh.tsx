import { useEffect, useRef, useState } from 'react'

interface PullToRefreshProps {
  onRefresh: () => Promise<void>
  threshold?: number
  children: React.ReactNode
}

export function PullToRefresh({
  onRefresh,
  threshold = 80,
  children,
}: PullToRefreshProps) {
  const [pullDistance, setPullDistance] = useState(0)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const startY = useRef(0)
  const isPulling = useRef(false)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleTouchStart = (e: TouchEvent) => {
      if (container.scrollTop > 0) return
      startY.current = e.touches[0].clientY
      isPulling.current = true
    }

    const handleTouchMove = (e: TouchEvent) => {
      if (!isPulling.current || isRefreshing) return
      if (container.scrollTop > 0) return

      const deltaY = e.touches[0].clientY - startY.current
      if (deltaY > 0) {
        e.preventDefault()
        const distance = Math.min(deltaY * 0.5, threshold * 2)
        setPullDistance(distance)
      }
    }

    const handleTouchEnd = async () => {
      if (!isPulling.current || isRefreshing) return
      isPulling.current = false

      if (pullDistance > threshold) {
        setIsRefreshing(true)
        try {
          await onRefresh()
          const capacitor = (
            window as unknown as { Capacitor?: { getPlatform?: () => string } }
          ).Capacitor
          const platform = capacitor?.getPlatform?.()
          if (platform === 'ios' || platform === 'android') {
            window.navigator?.vibrate?.(50)
          }
        } catch (error) {
          console.error('Refresh failed:', error)
        } finally {
          setIsRefreshing(false)
          setPullDistance(0)
        }
      } else {
        setPullDistance(0)
      }
    }

    container.addEventListener('touchstart', handleTouchStart, { passive: false })
    container.addEventListener('touchmove', handleTouchMove, { passive: false })
    container.addEventListener('touchend', handleTouchEnd)

    return () => {
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', handleTouchEnd)
    }
  }, [onRefresh, threshold, pullDistance, isRefreshing])

  return (
    <div
      ref={containerRef}
      style={{
        overflowY: 'auto',
        WebkitOverflowScrolling: 'touch',
        height: '100%',
      }}
    >
      <div
        style={{
          height: `${pullDistance}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--tp-surface)',
          borderBottom: '1px solid var(--tp-border)',
          transition: 'height 0.2s ease',
        }}
      >
        {isRefreshing ? (
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
        ) : pullDistance > 0 ? (
          <svg
            className={`h-6 w-6 text-muted-foreground transition-transform ${
              pullDistance > threshold ? 'rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 15l7-7 7 7"
            />
          </svg>
        ) : null}
      </div>
      {children}
    </div>
  )
}

export default PullToRefresh