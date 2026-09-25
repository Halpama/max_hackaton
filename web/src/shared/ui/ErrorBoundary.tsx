import React from 'react'
import { Button } from '@maxhub/max-ui'
import { PageLayout } from '@/shared/ui/PageLayout'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: React.ErrorInfo
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    this.setState({ error, errorInfo })

    // Log to console for development
    console.error('Uncaught error:', error, errorInfo)

    // Send to analytics/reporting service
    if (typeof window !== 'undefined') {
      const bridge = (
        window as unknown as {
          MaxBridge?: { sendEvent?: (event: Record<string, unknown>) => void }
        }
      ).MaxBridge
      bridge?.sendEvent?.({
        name: 'error',
        properties: {
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          type: 'ReactError',
        },
      })
    }
  }

  handleReload = (): void => {
    window.location.reload()
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <PageLayout>
          <div className="error-boundary text-center py-12">
            <div className="mb-6">
              <svg
                className="mx-auto h-16 w-16 text-red-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold mb-4">Что-то пошло не так</h2>
            <p className="text-muted-foreground mb-6">
              Мы столкнулись с неожиданной ошибкой. Не волнуйтесь, ваши данные в безопасности.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <Button stretched onClick={this.handleReload}>
                Попробовать снова
              </Button>
              <Button
                stretched
                variant="secondary"
                onClick={() => window.history.back()}
              >
                Назад
              </Button>
            </div>
            {import.meta.env.DEV && this.state.error && (
              <details className="mt-8 text-left max-w-2xl mx-auto">
                <summary className="cursor-pointer text-sm text-muted-foreground">
                  Показать детали ошибки
                </summary>
                <pre className="mt-2 p-4 bg-muted rounded text-xs overflow-auto">
                  <code>
                    {this.state.error.toString()}
                    {'\n\n'}
                    {this.state.errorInfo?.componentStack}
                  </code>
                </pre>
              </details>
            )}
          </div>
        </PageLayout>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary