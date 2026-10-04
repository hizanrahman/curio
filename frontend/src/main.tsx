import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter/wght.css'
import '@fontsource-variable/bricolage-grotesque/wght.css'
import '@fontsource-variable/jetbrains-mono/wght.css'
import './index.css'
import App from './App.tsx'
import { APP_NAME, APP_TAGLINE } from './config'

document.title = `${APP_NAME} — ${APP_TAGLINE}`
const description = document.querySelector<HTMLMetaElement>('meta[name="description"]')
if (description) description.content = `${APP_NAME} helps you learn how to work through problems with guided hints.`

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
