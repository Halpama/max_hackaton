import {
  useEffect,
  useRef,
  type KeyboardEvent as ReactKeyboardEvent,
} from 'react'
import type { PackingBlock } from '../model/useTripLocalState'
import { BulletListIcon, ChecklistIcon, TextBlockIcon } from './icons'
import styles from './PackingPanel.module.css'

interface PackingPanelProps {
  blocks: PackingBlock[]
  onChange: (blocks: PackingBlock[]) => void
  createId: () => string
}

type BlockType = PackingBlock['type']

function sameTypeBlock(type: BlockType, id: string): PackingBlock {
  if (type === 'check') return { id, type: 'check', text: '', done: false }
  if (type === 'bullet') return { id, type: 'bullet', text: '' }
  return { id, type: 'text', text: '' }
}

function detectShortcut(
  text: string,
):
  | { type: 'check'; text: string; done: boolean }
  | { type: 'bullet'; text: string }
  | null {
  if (/^\[x\]\s/i.test(text)) {
    return { type: 'check', text: text.replace(/^\[x\]\s/i, ''), done: true }
  }
  if (/^\[\s?\]\s/.test(text) || /^\[\]\s/.test(text)) {
    return {
      type: 'check',
      text: text.replace(/^\[\s?\]\s/, '').replace(/^\[\]\s/, ''),
      done: false,
    }
  }
  if (/^[-*]\s/.test(text)) {
    return { type: 'bullet', text: text.replace(/^[-*]\s/, '') }
  }
  return null
}

export function PackingPanel({ blocks, onChange, createId }: PackingPanelProps) {
  const focusIdRef = useRef<string | null>(null)
  const caretRef = useRef<number | null>(null)

  useEffect(() => {
    if (!focusIdRef.current) return
    const el = document.querySelector<HTMLElement>(
      `[data-packing-id="${focusIdRef.current}"]`,
    )
    if (!el) return
    el.focus()
    const caret = caretRef.current
    caretRef.current = null
    focusIdRef.current = null
    if (caret == null || !el.isContentEditable) return
    placeCaret(el, caret)
  }, [blocks])

  const commit = (next: PackingBlock[], focusId?: string, caret?: number) => {
    if (focusId) focusIdRef.current = focusId
    if (caret != null) caretRef.current = caret
    onChange(next)
  }

  const updateBlock = (id: string, patch: Partial<PackingBlock> & { type?: BlockType }) => {
    onChange(
      blocks.map((block) => {
        if (block.id !== id) return block
        if (patch.type && patch.type !== block.type) {
          if (patch.type === 'check') {
            return {
              id,
              type: 'check',
              text: patch.text ?? block.text,
              done: typeof patch.done === 'boolean' ? patch.done : false,
            }
          }
          if (patch.type === 'bullet') {
            return { id, type: 'bullet', text: patch.text ?? block.text }
          }
          return { id, type: 'text', text: patch.text ?? block.text }
        }
        return { ...block, ...patch } as PackingBlock
      }),
    )
  }

  const insertAfter = (id: string, block: PackingBlock) => {
    const index = blocks.findIndex((item) => item.id === id)
    const next = [...blocks]
    next.splice(index + 1, 0, block)
    commit(next, block.id, 0)
  }

  const removeBlock = (id: string) => {
    if (blocks.length <= 1) {
      commit([{ id: createId(), type: 'text', text: '' }], undefined)
      return
    }
    const index = blocks.findIndex((item) => item.id === id)
    const prev = blocks[index - 1]
    commit(
      blocks.filter((item) => item.id !== id),
      prev?.id ?? blocks[index + 1]?.id,
      prev ? prev.text.length : 0,
    )
  }

  const onTextInput = (block: PackingBlock, raw: string) => {
    const shortcut = block.type === 'text' ? detectShortcut(raw) : null
    if (shortcut) {
      if (shortcut.type === 'check') {
        updateBlock(block.id, { type: 'check', text: shortcut.text, done: shortcut.done })
      } else {
        updateBlock(block.id, { type: 'bullet', text: shortcut.text })
      }
      focusIdRef.current = block.id
      caretRef.current = shortcut.text.length
      return
    }
    updateBlock(block.id, { text: raw })
  }

  const onKeyDown = (block: PackingBlock, event: ReactKeyboardEvent<HTMLElement>) => {
    const text = block.text

    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if ((block.type === 'check' || block.type === 'bullet') && text.trim() === '') {
        updateBlock(block.id, { type: 'text', text: '' })
        focusIdRef.current = block.id
        return
      }
      insertAfter(block.id, sameTypeBlock(block.type, createId()))
      return
    }

    if (event.key === 'Backspace') {
      const selection = window.getSelection()
      const atStart =
        selection?.anchorOffset === 0 &&
        selection.isCollapsed &&
        selection.anchorNode &&
        (event.currentTarget === selection.anchorNode ||
          event.currentTarget.contains(selection.anchorNode))

      if (text === '') {
        event.preventDefault()
        if (block.type !== 'text') {
          updateBlock(block.id, { type: 'text', text: '' })
          return
        }
        removeBlock(block.id)
        return
      }

      if (atStart && block.type !== 'text') {
        event.preventDefault()
        updateBlock(block.id, { type: 'text', text })
      }
    }
  }

  const turnInto = (type: BlockType) => {
    const focused = document.activeElement as HTMLElement | null
    const focusedId = focused?.getAttribute?.('data-packing-id')
    const targetId = focusedId ?? blocks[blocks.length - 1]?.id
    if (!targetId) {
      commit([sameTypeBlock(type, createId())], undefined)
      return
    }
    const current = blocks.find((b) => b.id === targetId)
    if (!current) return
    if (current.type === type) return
    updateBlock(targetId, {
      type,
      text: current.text,
      ...(type === 'check' ? { done: false } : {}),
    })
    focusIdRef.current = targetId
  }

  const ensureTail = () => {
    const last = blocks[blocks.length - 1]
    if (last && last.type === 'text' && last.text === '') {
      focusIdRef.current = last.id
      requestAnimationFrame(() => {
        document.querySelector<HTMLElement>(`[data-packing-id="${last.id}"]`)?.focus()
      })
      return
    }
    const id = createId()
    commit([...blocks, { id, type: 'text', text: '' }], id, 0)
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.topBar}>
        <p className={styles.hint}>Чеклист вещей и заметки к поездке.</p>
        <div className={styles.toolbar} role="toolbar" aria-label="Тип блока">
          <button
            type="button"
            className={styles.tool}
            aria-label="Текст"
            title="Текст"
            onClick={() => turnInto('text')}
          >
            <TextBlockIcon />
          </button>
          <button
            type="button"
            className={styles.tool}
            aria-label="Список"
            title="Список"
            onClick={() => turnInto('bullet')}
          >
            <BulletListIcon />
          </button>
          <button
            type="button"
            className={styles.tool}
            aria-label="Чеклист"
            title="Чеклист"
            onClick={() => turnInto('check')}
          >
            <ChecklistIcon />
          </button>
        </div>
      </div>

      <div className={styles.editor} onClick={(event) => {
        if (event.target === event.currentTarget) ensureTail()
      }}>
        <div className={styles.page}>
          {blocks.map((block) => (
            <div
              key={block.id}
              className={
                block.type === 'text'
                  ? styles.blockText
                  : block.type === 'bullet'
                    ? styles.blockBullet
                    : styles.blockCheck
              }
            >
              {block.type === 'check' ? (
                <button
                  type="button"
                  className={block.done ? styles.checkOn : styles.check}
                  tabIndex={-1}
                  aria-label={block.done ? 'Снять отметку' : 'Отметить'}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => updateBlock(block.id, { done: !block.done })}
                >
                  {block.done ? (
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden>
                      <path
                        d="M5 12.5l5 5L19 7"
                        stroke="currentColor"
                        strokeWidth="2.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  ) : null}
                </button>
              ) : null}

              {block.type === 'bullet' ? <span className={styles.bullet} aria-hidden /> : null}

              <EditableLine
                id={block.id}
                text={block.text}
                done={block.type === 'check' ? block.done : false}
                placeholder={
                  block.type === 'check'
                    ? 'Пункт чеклиста'
                    : block.type === 'bullet'
                      ? 'Пункт списка'
                      : 'Начните писать…'
                }
                onInput={(value) => onTextInput(block, value)}
                onKeyDown={(event) => onKeyDown(block, event)}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function EditableLine({
  id,
  text,
  done,
  placeholder,
  onInput,
  onKeyDown,
}: {
  id: string
  text: string
  done: boolean
  placeholder: string
  onInput: (value: string) => void
  onKeyDown: (event: ReactKeyboardEvent<HTMLElement>) => void
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (el.textContent === text) return
    el.textContent = text
    if (document.activeElement === el) {
      placeCaret(el, text.length)
    }
  }, [text])

  return (
    <div
      ref={ref}
      data-packing-id={id}
      className={done ? styles.lineDone : styles.line}
      contentEditable
      role="textbox"
      aria-multiline="false"
      suppressContentEditableWarning
      data-placeholder={placeholder}
      onInput={(event) => {
        const el = event.currentTarget
        const value = (el.textContent ?? '').replace(/\n/g, '')
        if (el.textContent !== value) el.textContent = value
        onInput(value)
      }}
      onKeyDown={onKeyDown}
      onPaste={(event) => {
        event.preventDefault()
        const plain = event.clipboardData.getData('text/plain').replace(/\n/g, ' ')
        document.execCommand('insertText', false, plain)
      }}
    />
  )
}

function placeCaret(el: HTMLElement, offset: number) {
  const textNode = el.firstChild
  const selection = window.getSelection()
  if (!selection) return
  const range = document.createRange()
  if (textNode && textNode.nodeType === Node.TEXT_NODE) {
    const safe = Math.min(offset, textNode.textContent?.length ?? 0)
    range.setStart(textNode, safe)
    range.collapse(true)
  } else {
    range.selectNodeContents(el)
    range.collapse(true)
  }
  selection.removeAllRanges()
  selection.addRange(range)
}
