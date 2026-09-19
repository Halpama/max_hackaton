import { useEffect, useRef, useState } from 'react'
import styles from './SoftImage.module.css'

type SoftImageProps = {
  src: string
  alt?: string
  className?: string
  /** Applied to the shimmer overlay (border-radius etc.). Defaults to className. */
  skeletonClassName?: string
  loading?: 'lazy' | 'eager'
  onError?: () => void
}

/**
 * Keeps layout from the image box and fades the photo in over a shimmer.
 * Opacity lives on an inner wrapper so parent `transition: transform` cannot
 * wipe the fade.
 */
export function SoftImage({
  src,
  alt = '',
  className,
  skeletonClassName,
  loading = 'lazy',
  onError,
}: SoftImageProps) {
  const ref = useRef<HTMLImageElement>(null)
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)
  const [showSkeleton, setShowSkeleton] = useState(true)

  useEffect(() => {
    setLoaded(false)
    setFailed(false)
    setShowSkeleton(true)
    const node = ref.current
    if (node?.complete && node.naturalWidth > 0) {
      // Cached: still paint one frame at opacity 0, then fade in.
      requestAnimationFrame(() => setLoaded(true))
    }
  }, [src])

  useEffect(() => {
    if (!loaded) return
    const id = window.setTimeout(() => setShowSkeleton(false), 750)
    return () => window.clearTimeout(id)
  }, [loaded])

  if (failed) return null

  return (
    <span className={styles.wrap}>
      {showSkeleton ? (
        <span
          className={`${styles.skeleton} ${loaded ? styles.skeletonOut : ''} ${skeletonClassName ?? className ?? ''}`}
          aria-hidden
        />
      ) : null}
      <span className={`${styles.fade} ${loaded ? styles.fadeIn : styles.fadeOut}`}>
        <img
          ref={ref}
          className={className}
          src={src}
          alt={alt}
          loading={loading}
          decoding="async"
          onLoad={() => setLoaded(true)}
          onError={() => {
            setFailed(true)
            setShowSkeleton(false)
            onError?.()
          }}
        />
      </span>
    </span>
  )
}
