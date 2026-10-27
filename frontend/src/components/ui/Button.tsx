import Link from 'next/link'
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/format'
import { Spinner } from './Spinner'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'

const VARIANTS: Record<ButtonVariant, string> = {
  // Lime fill, charcoal-1000 text (the single charged accent).
  primary: 'bg-apple-500 text-charcoal-1000 hover:bg-apple-300 disabled:bg-apple-800 disabled:text-charcoal-950',
  secondary: 'border border-hairline bg-transparent text-cloud hover:bg-charcoal-750 hover:border-[#4a4e56]',
  ghost: 'bg-transparent text-cloud hover:bg-charcoal-750',
  danger: 'border border-mute-red/50 bg-mute-red/10 text-[#ff8197] hover:bg-mute-red/20',
}

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-11 px-5 text-base gap-2',
}

export function buttonClasses(variant: ButtonVariant = 'primary', size: ButtonSize = 'md', className?: string): string {
  return cn(
    'inline-flex select-none items-center justify-center whitespace-nowrap rounded font-medium',
    'transition-colors duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-70',
    VARIANTS[variant],
    SIZES[size],
    className,
  )
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading = false, icon, className, children, disabled, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={buttonClasses(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner /> : icon ? <span aria-hidden="true">{icon}</span> : null}
      {children}
    </button>
  )
})

interface ButtonLinkProps {
  href: string
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
  icon?: ReactNode
  children: ReactNode
}

export function ButtonLink({ href, variant = 'primary', size = 'md', className, icon, children }: ButtonLinkProps) {
  return (
    <Link href={href} className={buttonClasses(variant, size, className)}>
      {children}
      {icon && <span aria-hidden="true">{icon}</span>}
    </Link>
  )
}
