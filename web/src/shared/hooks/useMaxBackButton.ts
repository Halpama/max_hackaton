import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getWebApp } from '@/shared/lib/max'

/**
 * Syncs MAX system BackButton with react-router history.
 * Shows the button when `canGoBack` is true.
 */
export function useMaxBackButton(canGoBack: boolean) {
  const navigate = useNavigate()

  useEffect(() => {
    const backButton = getWebApp()?.BackButton
    if (!backButton) {
      return
    }

    const onClick = () => {
      navigate(-1)
    }

    if (canGoBack) {
      backButton.show()
      backButton.onClick(onClick)
    } else {
      backButton.hide()
    }

    return () => {
      backButton.offClick(onClick)
      backButton.hide()
    }
  }, [canGoBack, navigate])
}
