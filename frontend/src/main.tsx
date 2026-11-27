import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { BuilderPrototype } from './prototype/builder'

// PROTOTYPE route: /prototype/builder (branch prototype/builder only)
const isPrototype = location.pathname.startsWith('/prototype/builder')

createRoot(document.getElementById('root')!).render(
  <StrictMode>{isPrototype ? <BuilderPrototype /> : <App />}</StrictMode>,
)
