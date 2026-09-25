import { defineConfig, mergeConfig } from 'vite'
import baseConfig from './vite.config'

/** Same as production build; use when you want a dedicated analyze entrypoint. */
export default mergeConfig(baseConfig, defineConfig({}))
