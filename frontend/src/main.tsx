import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import './index.css'
import App from './App'

const theme = createTheme({ palette: { primary: { main: '#126a50' }, background: { default: '#f6f7f5' } }, shape: { borderRadius: 10 } })

createRoot(document.getElementById('root')!).render(<StrictMode><ThemeProvider theme={theme}><CssBaseline /><App /></ThemeProvider></StrictMode>)
