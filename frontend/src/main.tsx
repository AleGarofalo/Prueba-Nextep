import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ApiError } from './api/apiClient'
import { ToastProvider } from './components/ui/ToastContainer'
import { AppErrorBoundary } from './components/ui/AppErrorBoundary'
import './index.css'
import App from './App.tsx'

const client = new QueryClient({ defaultOptions: { queries: {
  staleTime: 15_000, refetchOnWindowFocus: false,
  retry: (count, error) => !(error instanceof ApiError && error.status > 0 && error.status < 500) && count < 1,
}, mutations: { retry: false } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppErrorBoundary><QueryClientProvider client={client}><ToastProvider><App /></ToastProvider></QueryClientProvider></AppErrorBoundary>
  </StrictMode>,
)
