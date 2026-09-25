import { useEffect } from 'react'

export function useBeforeUnloadSave() {
  useEffect(() => {
    const handleBeforeUnload = () => {
      // Trigger a final sync of localStorage data
      const event = new Event('sync-localstorage')
      window.dispatchEvent(event)
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [])
}