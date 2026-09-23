/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_USE_MOCKS?: string
  readonly VITE_YANDEX_MAPS_TILES_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
