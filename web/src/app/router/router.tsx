import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import { AppShell } from './AppShell'

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      {
        path: ROUTES.home,
        lazy: async () => {
          const { NewTripPage } = await import('@/pages/new-trip')
          return { Component: NewTripPage }
        },
      },
      {
        path: ROUTES.preferences,
        lazy: async () => {
          const { PreferencesPage } = await import('@/pages/preferences')
          return { Component: PreferencesPage }
        },
      },
      {
        path: ROUTES.loading,
        lazy: async () => {
          const { RouteLoadingPage } = await import('@/pages/route-loading')
          return { Component: RouteLoadingPage }
        },
      },
      {
        path: ROUTES.route,
        lazy: async () => {
          const { ReadyRoutePage } = await import('@/pages/ready-route')
          return { Component: ReadyRoutePage }
        },
      },
      {
        path: ROUTES.placePattern,
        lazy: async () => {
          const { LocationDetailPage } = await import('@/pages/location-detail')
          return { Component: LocationDetailPage }
        },
      },
      {
        path: '*',
        lazy: async () => {
          const { NotFoundPage } = await import('@/pages/not-found')
          return { Component: NotFoundPage }
        },
      },
    ],
  },
  {
    path: '/index.html',
    element: <Navigate to={ROUTES.home} replace />,
  },
])
