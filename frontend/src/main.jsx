import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { SesionProvider } from './context/SesionProvider.jsx'
import { ToastProvider } from './context/ToastProvider.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SesionProvider>
      <ToastProvider>
        <App />
      </ToastProvider>
    </SesionProvider>
  </StrictMode>,
)
