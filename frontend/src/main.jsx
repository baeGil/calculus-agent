import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

import ErrorBoundary from './components/ErrorBoundary.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary fallback={<div className="p-4 text-red-500"><h1>Application Crashed</h1><p>Check console for details.</p></div>}>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
