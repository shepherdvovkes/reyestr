import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authApi, AuthResponse } from '../api/auth'

interface AuthContextType {
  isAuthenticated: boolean
  user: AuthResponse['user'] | null
  login: (username: string) => Promise<void>
  logout: () => Promise<void>
  register: (username: string, displayName: string) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState<AuthResponse['user'] | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      // Verify token is still valid
      setIsAuthenticated(true)
      // TODO: Fetch user info from token
    }
  }, [])

  const login = async (username: string) => {
    try {
      // Step 1: Get challenge from server
      const challenge = await authApi.loginStart(username)

      // Step 2: Convert challenge to PublicKeyCredentialRequestOptions
      const publicKey: PublicKeyCredentialRequestOptions = {
        challenge: Uint8Array.from(atob(challenge.challenge), (c) => c.charCodeAt(0)),
        allowCredentials: challenge.allowCredentials?.map((cred) => ({
          id: Uint8Array.from(atob(cred.id), (c) => c.charCodeAt(0)),
          type: cred.type,
          transports: cred.transports,
        })),
        timeout: challenge.timeout,
        userVerification: challenge.userVerification as UserVerificationRequirement,
        rpId: challenge.rpId,
      }

      // Step 3: Request credential from authenticator
      const credential = (await navigator.credentials.get({
        publicKey,
      })) as PublicKeyCredential | null

      if (!credential) {
        throw new Error('No credential returned')
      }

      // Step 4: Send credential to server
      const response = await authApi.loginComplete(credential)

      // Step 5: Store token and user info
      localStorage.setItem('auth_token', response.token)
      setUser(response.user)
      setIsAuthenticated(true)
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  }

  const register = async (username: string, displayName: string) => {
    try {
      // Step 1: Get challenge from server
      const challenge = await authApi.registerStart(username, displayName)

      // Step 2: Convert challenge to PublicKeyCredentialCreationOptions
      const publicKey: PublicKeyCredentialCreationOptions = {
        challenge: Uint8Array.from(atob(challenge.challenge), (c) => c.charCodeAt(0)),
        rp: challenge.rp,
        user: {
          id: Uint8Array.from(atob(challenge.user.id), (c) => c.charCodeAt(0)),
          name: challenge.user.name,
          displayName: challenge.user.displayName,
        },
        pubKeyCredParams: challenge.pubKeyCredParams,
        authenticatorSelection: challenge.authenticatorSelection,
        timeout: challenge.timeout,
        attestation: challenge.attestation as AttestationConveyancePreference,
      }

      // Step 3: Request credential from authenticator
      const credential = (await navigator.credentials.create({
        publicKey,
      })) as PublicKeyCredential | null

      if (!credential) {
        throw new Error('No credential returned')
      }

      // Step 4: Send credential to server
      const response = await authApi.registerComplete(credential)

      // Step 5: Store token and user info
      localStorage.setItem('auth_token', response.token)
      setUser(response.user)
      setIsAuthenticated(true)
    } catch (error) {
      console.error('Registration error:', error)
      throw error
    }
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('auth_token')
      setUser(null)
      setIsAuthenticated(false)
    }
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
