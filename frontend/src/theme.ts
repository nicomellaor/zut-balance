import { createTheme, responsiveFontSizes } from '@mui/material/styles'

export const chartColors = ['#592C82', '#34758A', '#398275', '#B66A1E', '#A65078']

let theme = createTheme({
  palette: {
    primary: { main: '#592C82', light: '#E9DDF4', dark: '#3D1D5D', contrastText: '#FFFFFF' },
    info: { main: '#34758A' },
    warning: { main: '#B66A1E' },
    background: { default: '#F5F5F8', paper: '#FFFFFF' },
    text: { primary: '#272330', secondary: '#625C6B' },
    divider: '#DDD9E2',
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: 'IBM Plex Sans Variable, IBM Plex Sans, sans-serif',
    h1: { fontSize: '2rem', fontWeight: 600, lineHeight: 1.15, letterSpacing: '-0.03em' },
    h2: { fontSize: '1.5rem', fontWeight: 600, lineHeight: 1.25, letterSpacing: '-0.02em' },
    h3: { fontSize: '1.25rem', fontWeight: 600, lineHeight: 1.3 },
    h4: { fontSize: '1.125rem', fontWeight: 600, lineHeight: 1.35 },
    button: { fontWeight: 600, textTransform: 'none' },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { minWidth: 320 },
        '*:focus-visible': { outline: '3px solid #8060A8', outlineOffset: 2 },
        '@media (prefers-reduced-motion: reduce)': { '*': { scrollBehavior: 'auto !important', transitionDuration: '0.01ms !important' } },
      },
    },
    MuiPaper: { styleOverrides: { root: { border: '1px solid #DDD9E2', boxShadow: 'none' } } },
    MuiCard: { styleOverrides: { root: { border: '1px solid #DDD9E2', boxShadow: 'none' } } },
    MuiButton: { styleOverrides: { root: { borderRadius: 8 } } },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: '#DDD9E2', padding: '10px 12px', verticalAlign: 'top' },
        head: { color: '#625C6B', fontSize: '0.75rem', fontWeight: 600, whiteSpace: 'nowrap' },
      },
    },
  },
})

theme = responsiveFontSizes(theme, { factor: 2.5 })

export default theme
