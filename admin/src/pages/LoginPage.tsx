import { useState } from 'react'
import {
  Container,
  Paper,
  Box,
  TextField,
  Button,
  Typography,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
} from '@mui/material'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`auth-tabpanel-${index}`}
      aria-labelledby={`auth-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  )
}

export default function LoginPage() {
  const [tab, setTab] = useState(0)
  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await login(username)
      navigate('/')
    } catch (err: any) {
      setError(err.message || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await register(username, displayName)
      navigate('/')
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Paper sx={{ p: 4, width: '100%' }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Reyestr Admin
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
            WebAuthn Authentication
          </Typography>

          <Tabs value={tab} onChange={(_, newValue) => setTab(newValue)}>
            <Tab label="Login" />
            <Tab label="Register" />
          </Tabs>

          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}

          <TabPanel value={tab} index={0}>
            <Box component="form" onSubmit={handleLogin}>
              <TextField
                fullWidth
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                margin="normal"
                required
                disabled={loading}
                autoComplete="username"
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={loading || !username}
              >
                {loading ? <CircularProgress size={24} /> : 'Login with WebAuthn'}
              </Button>
              <Typography variant="body2" color="text.secondary" align="center">
                Use your YubiKey or phone to authenticate
              </Typography>
            </Box>
          </TabPanel>

          <TabPanel value={tab} index={1}>
            <Box component="form" onSubmit={handleRegister}>
              <TextField
                fullWidth
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                margin="normal"
                required
                disabled={loading}
                autoComplete="username"
              />
              <TextField
                fullWidth
                label="Display Name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                margin="normal"
                required
                disabled={loading}
                autoComplete="name"
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={loading || !username || !displayName}
              >
                {loading ? <CircularProgress size={24} /> : 'Register with WebAuthn'}
              </Button>
              <Typography variant="body2" color="text.secondary" align="center">
                Register a new account with WebAuthn
              </Typography>
            </Box>
          </TabPanel>
        </Paper>
      </Box>
    </Container>
  )
}
