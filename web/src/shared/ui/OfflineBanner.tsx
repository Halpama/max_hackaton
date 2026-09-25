import { useEffect, useState } from 'react'

interface OfflineBannerProps {
  message?: string
  reconnectMessage?: string
}

export function OfflineBanner({
  message = 'Нет подключения к интернету',
  reconnectMessage = 'Попытка переподключения...',
}: OfflineBannerProps) {
  const [isOffline, setIsOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const handleOnline = () => setIsOffline(false)
    const handleOffline = () => setIsOffline(true)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  if (!isOffline) return null

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center px-4 py-2 text-sm font-medium bg-red-500 text-white"
      role="status"
      aria-live="assertive"
    >
      <div className="flex items-center gap-2">
        <svg
          className="w-4 h-4 animate-pulse"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3M6.26 6.26a5.86 5.86 0 0 1 8.48 8.48M18.74 18.74a5.86 5.86 0 0 1-8.48 8.48M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"
          />
        </svg>
        <span>{message}</span>
        <span className="opacity-80">{reconnectMessage}</span>
      </div>
    </div>
  )
}