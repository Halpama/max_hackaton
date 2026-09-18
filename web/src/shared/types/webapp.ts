export interface WebAppUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  language_code?: string
  photo_url?: string
}

export interface WebAppChat {
  id: number
  type: 'DIALOG' | 'CHAT' | 'CHANNEL'
}

export interface WebAppInitData {
  query_id?: string
  ip?: string
  auth_date?: number
  hash?: string
  user?: WebAppUser
  chat?: WebAppChat
  start_param?: string
}

export interface WebAppBackButton {
  isVisible: boolean
  show: () => void
  hide: () => void
  onClick: (callback: () => void) => void
  offClick: (callback: () => void) => void
}

export interface MaxWebApp {
  initData: string
  initDataUnsafe: WebAppInitData
  platform: 'ios' | 'android' | 'desktop' | 'web' | string
  version: string
  deviceName?: string
  ready?: () => void
  close?: () => void
  BackButton?: WebAppBackButton
  openLink?: (url: string) => Promise<unknown>
  openMaxLink?: (url: string) => Promise<unknown>
}
