import { Button, Typography } from '@maxhub/max-ui'
import { Link } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import { PageLayout } from '@/shared/ui'

export function NotFoundPage() {
  return (
    <PageLayout centered>
      <Typography.Title>Страница не найдена</Typography.Title>
      <Typography.Body>Проверьте адрес или вернитесь к поездке</Typography.Body>
      <Button stretched asChild>
        <Link to={ROUTES.home}>К новой поездке</Link>
      </Button>
    </PageLayout>
  )
}
