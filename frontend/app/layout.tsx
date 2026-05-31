import type { Metadata, Viewport } from 'next'
import { DM_Sans, JetBrains_Mono, Noto_Serif } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/components/theme-provider'
import { SystemStatusProvider } from '@/components/SystemStatusProvider'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { cn } from '@/lib/utils'

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
  weight: ['300', '400', '500', '600', '700'],
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
  weight: ['400', '500', '600'],
})

const notoSerif = Noto_Serif({
  subsets: ['latin'],
  variable: '--font-serif',
  display: 'swap',
})

export const viewport: Viewport = {
  themeColor: '#0D0D0D',
  width: 'device-width',
  initialScale: 1,
}

export const metadata: Metadata = {
  title: 'AStock 市场认知引擎',
  description: 'A股市场行为逻辑分析系统',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning
      className={cn('dark', dmSans.variable, jetbrainsMono.variable, notoSerif.variable)}>
      <body className="font-sans">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <ErrorBoundary>
            <SystemStatusProvider>
              {children}
            </SystemStatusProvider>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  )
}
