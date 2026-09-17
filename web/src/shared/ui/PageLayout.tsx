import type { CSSProperties, ReactNode } from 'react'
import { Flex, Panel } from '@maxhub/max-ui'

interface PageLayoutProps {
  children: ReactNode
  centered?: boolean
  style?: CSSProperties
}

export function PageLayout({ children, centered = false, style }: PageLayoutProps) {
  return (
    <Panel
      mode="primary"
      centeredX={centered}
      centeredY={centered}
      style={{ minHeight: '100dvh', padding: 24, ...style }}
    >
      <Flex
        direction="column"
        align={centered ? 'center' : 'stretch'}
        gap={16}
        style={{ width: '100%', maxWidth: centered ? 360 : 720, marginInline: 'auto' }}
      >
        {children}
      </Flex>
    </Panel>
  )
}
