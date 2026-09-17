import { Avatar, Button, Flex, Typography } from '@maxhub/max-ui'
import { closeWebApp } from '@/shared/lib/max'
import { useMaxUser, useMaxWebApp } from '@/shared/hooks'
import { PageLayout } from '@/shared/ui'
import { getUserDisplayName, getUserInitials } from '@/shared/utils'

export function HomePage() {
  const user = useMaxUser()
  const { isMax, platform, version, startParam, webApp } = useMaxWebApp()

  const displayName = getUserDisplayName(user)
  const initials = getUserInitials(user)

  return (
    <PageLayout centered>
      <Avatar.Container size={64}>
        {user?.photo_url ? (
          <Avatar.Image src={user.photo_url} alt={displayName} />
        ) : (
          <Avatar.Text>{initials}</Avatar.Text>
        )}
      </Avatar.Container>

      <Flex direction="column" align="center" gap={4}>
        <Typography.Title>{displayName}</Typography.Title>
        {user?.username ? <Typography.Body>@{user.username}</Typography.Body> : null}
      </Flex>

      <Flex direction="column" gap={8} style={{ width: '100%' }}>
        <Typography.Label>
          {isMax
            ? `MAX Bridge · ${platform ?? 'unknown'} · ${version ?? '—'}`
            : 'Запущено вне клиента MAX — Bridge недоступен'}
        </Typography.Label>
        {startParam ? <Typography.Text>start_param: {startParam}</Typography.Text> : null}
      </Flex>

      {isMax && webApp?.close ? (
        <Button stretched onClick={closeWebApp}>
          Закрыть
        </Button>
      ) : null}
    </PageLayout>
  )
}
