import { useEffect, useId, useState, type FormEvent } from 'react'
import { createPortal } from 'react-dom'
import {
  formatDayHeading,
  formatMoney,
  groupLedgerByDate,
  type LedgerEntry,
  type LedgerKind,
} from '../../model/useTripLocalState'
import { PlusIcon } from '../shared/icons'
import styles from './BudgetPanel.module.css'

interface BudgetPanelProps {
  plannedBudget: number
  remaining: number
  spent: number
  toppedUp: number
  ledger: LedgerEntry[]
  todayIso: () => string
  onAdd: (input: { kind: LedgerKind; amount: number; title: string; date: string }) => void
  onRemove: (id: string) => void
}

export function BudgetPanel({
  plannedBudget,
  remaining,
  spent,
  toppedUp,
  ledger,
  todayIso,
  onAdd,
  onRemove,
}: BudgetPanelProps) {
  const [modalOpen, setModalOpen] = useState(false)
  const netSpent = Math.max(0, spent - toppedUp)
  const usedRatio = Math.min(1, netSpent / Math.max(plannedBudget, 1))
  const overspent = remaining < 0
  const groups = groupLedgerByDate(ledger)

  return (
    <div className={styles.wrap}>
      <section className={styles.summary}>
        <div className={styles.summaryTop}>
          <div>
            <p className={styles.kicker}>Бюджет</p>
            <p className={styles.amount}>
              <span className={styles.amountValue}>{formatMoney(plannedBudget)}</span>
              <span className={styles.amountCurrency}>₽</span>
            </p>
          </div>
          <div className={styles.remainBlock}>
            <p className={overspent ? styles.kickerWarn : styles.kickerRemain}>
              {overspent ? 'Перерасход' : 'Осталось'}
            </p>
            <p className={overspent ? styles.amountWarn : styles.amountRemain}>
              <span className={styles.amountValue}>{formatMoney(Math.abs(remaining))}</span>
              <span className={styles.amountCurrency}>₽</span>
            </p>
          </div>
        </div>

        <div className={styles.barTrack} aria-hidden>
          <div
            className={overspent ? styles.barFillWarn : styles.barFill}
            style={{ width: `${Math.min(100, usedRatio * 100)}%` }}
          />
        </div>

        <div className={styles.metaRow}>
          <span>Потрачено {formatMoney(spent)} ₽</span>
          {toppedUp > 0 ? <span>· Пополнено {formatMoney(toppedUp)} ₽</span> : null}
          <span>· {Math.round(usedRatio * 100)}%</span>
        </div>
      </section>

      <button type="button" className={styles.addBtn} onClick={() => setModalOpen(true)}>
        <PlusIcon />
        Добавить трату / пополнение
      </button>

      <section className={styles.history}>
        {groups.length === 0 ? (
          <p className={styles.empty}>Пока нет операций — добавьте первую трату или пополнение.</p>
        ) : (
          groups.map((group) => (
            <div key={group.date} className={styles.dayGroup}>
              <h3 className={styles.dayLabel}>{formatDayHeading(group.date)}</h3>
              <ul className={styles.dayList}>
                {group.items.map((entry) => {
                  const kindLabel = entry.kind === 'expense' ? 'Трата' : 'Пополнение'
                  const title =
                    entry.title.trim() && entry.title.trim() !== kindLabel
                      ? entry.title.trim()
                      : kindLabel
                  const showKind = title !== kindLabel

                  return (
                    <li key={entry.id} className={styles.entry}>
                      <div className={styles.entryMain}>
                        <p className={styles.entryTitle}>{title}</p>
                        {showKind ? <p className={styles.entryKind}>{kindLabel}</p> : null}
                      </div>
                      <p
                        className={
                          entry.kind === 'expense' ? styles.entryAmountOut : styles.entryAmountIn
                        }
                      >
                        {entry.kind === 'expense' ? '−' : '+'}
                        {formatMoney(entry.amount)} ₽
                      </p>
                      <button
                        type="button"
                        className={styles.entryRemove}
                        aria-label="Удалить"
                        onClick={() => onRemove(entry.id)}
                      >
                        ×
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))
        )}
      </section>

      {modalOpen ? (
        <BudgetModal
          defaultDate={todayIso()}
          onClose={() => setModalOpen(false)}
          onSubmit={(payload) => {
            onAdd(payload)
            setModalOpen(false)
          }}
        />
      ) : null}
    </div>
  )
}

function BudgetModal({
  defaultDate,
  onClose,
  onSubmit,
}: {
  defaultDate: string
  onClose: () => void
  onSubmit: (payload: { kind: LedgerKind; amount: number; title: string; date: string }) => void
}) {
  const titleId = useId()
  const [kind, setKind] = useState<LedgerKind>('expense')
  const [amount, setAmount] = useState('')
  const [title, setTitle] = useState('')
  const [date, setDate] = useState(defaultDate)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const value = Number(amount.replace(/\s/g, '').replace(',', '.'))
    if (!Number.isFinite(value) || value <= 0) return
    onSubmit({ kind, amount: value, title, date })
  }

  return createPortal(
    <div className={styles.modalRoot} role="presentation" onClick={onClose}>
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <div className={styles.modalHandle} aria-hidden />
        <h2 id={titleId} className={styles.modalTitle}>
          Новая операция
        </h2>

        <div className={styles.kindSwitch} role="tablist" aria-label="Тип операции">
          <button
            type="button"
            className={kind === 'expense' ? styles.kindActive : styles.kind}
            onClick={() => setKind('expense')}
          >
            Трата
          </button>
          <button
            type="button"
            className={kind === 'topup' ? styles.kindActive : styles.kind}
            onClick={() => setKind('topup')}
          >
            Пополнение
          </button>
        </div>

        <form className={styles.form} onSubmit={submit}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Сумма</span>
            <input
              className={styles.fieldInput}
              inputMode="decimal"
              placeholder="0"
              value={amount}
              autoFocus
              onChange={(event) => setAmount(event.target.value.replace(/[^\d\s.,]/g, ''))}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Название</span>
            <input
              className={styles.fieldInput}
              placeholder={kind === 'expense' ? 'Кофе, билеты…' : 'Снял в банкомате…'}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Дата</span>
            <input
              className={styles.fieldInput}
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </label>

          <div className={styles.modalActions}>
            <button type="button" className={styles.cancelBtn} onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className={styles.saveBtn}>
              Сохранить
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  )
}
