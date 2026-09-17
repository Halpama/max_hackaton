import { useMemo } from 'react'
import {
  getInitDataUnsafe,
  getWebApp,
  getWebAppUser,
  isMaxWebApp,
} from '@/shared/lib/max'

export function useMaxWebApp() {
  return useMemo(() => {
    const webApp = getWebApp()
    const initDataUnsafe = getInitDataUnsafe()

    return {
      webApp,
      isMax: isMaxWebApp(),
      platform: webApp?.platform,
      version: webApp?.version,
      initDataUnsafe,
      startParam: initDataUnsafe?.start_param,
    }
  }, [])
}

export function useMaxUser() {
  return useMemo(() => getWebAppUser(), [])
}
