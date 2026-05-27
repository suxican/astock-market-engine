import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'AStock AI Copilot V2 - 市场认知引擎',
  description: '真正理解A股市场行为逻辑的AI认知系统',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className={`${inter.variable} font-sans`}>
        {children}
      </body>
    </html>
  )
}
