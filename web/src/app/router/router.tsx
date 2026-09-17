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
          const { HomePage } = await import('@/pages/home')
          return { Component: HomePage }
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
