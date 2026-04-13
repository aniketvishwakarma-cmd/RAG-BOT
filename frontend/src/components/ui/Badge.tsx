import clsx from 'clsx'
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  className?: string
}

export function Badge({ children, className }: Props) {
  return (
    <span className={clsx('inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium', className)}>
      {children}
    </span>
  )
}

