import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { Button } from './Button'

export class AppErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('Inventory UI error', error, info) }
  render() {
    if (this.state.failed) return <main style={{ maxWidth: 580, margin: '15vh auto', padding: 24 }}><h1>Something went wrong</h1><p style={{ margin: '16px 0', color: 'var(--text-secondary)' }}>The inventory screen could not be displayed. Reload the page to try again.</p><Button variant="primary" onClick={() => window.location.reload()}>Reload inventory</Button></main>
    return this.props.children
  }
}
