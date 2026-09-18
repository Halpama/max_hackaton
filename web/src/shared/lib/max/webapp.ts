import type { MaxWebApp, WebAppInitData, WebAppUser } from '@/shared/types'

/** Safe access to MAX Bridge (`window.WebApp`). Absent outside the MAX client. */
export function getWebApp(): MaxWebApp | undefined {
  if (typeof window === 'undefined') {
    return undefined
  }

  return window.WebApp
}

export function isMaxWebApp(): boolean {
  return Boolean(getWebApp())
}

/** Signal that the mini-app UI is ready (hides client skeleton when supported). */
export function notifyWebAppReady(): void {
  getWebApp()?.ready?.()
}

export function closeWebApp(): void {
  getWebApp()?.close?.()
}

export function getInitData(): string {
  return getWebApp()?.initData ?? ''
}

export function getInitDataUnsafe(): WebAppInitData | undefined {
  return getWebApp()?.initDataUnsafe
}

export function getWebAppUser(): WebAppUser | undefined {
  return getInitDataUnsafe()?.user
}
