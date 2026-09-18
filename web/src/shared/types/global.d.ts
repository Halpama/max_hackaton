import type { MaxWebApp } from './webapp'

declare global {
  interface Window {
    WebApp?: MaxWebApp
  }
}
