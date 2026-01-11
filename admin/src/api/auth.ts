import { apiClient } from './client'

export interface WebAuthnRegisterRequest {
  username: string
  displayName: string
}

export interface WebAuthnLoginRequest {
  username: string
}

export interface AuthResponse {
  token: string
  user: {
    id: string
    username: string
    displayName: string
  }
}

export interface WebAuthnChallenge {
  challenge: string
  rp: {
    name: string
    id: string
  }
  user: {
    id: string
    name: string
    displayName: string
  }
  pubKeyCredParams: Array<{
    type: string
    alg: number
  }>
  authenticatorSelection?: {
    authenticatorAttachment?: string
    userVerification?: string
  }
  timeout: number
  attestation: string
  allowCredentials?: Array<{
    id: string
    type: string
    transports?: string[]
  }>
  rpId?: string
  userVerification?: string
}

export const authApi = {
  async registerStart(username: string, displayName: string): Promise<WebAuthnChallenge> {
    const response = await apiClient.post<WebAuthnChallenge>('/auth/webauthn/register/start', {
      username,
      displayName,
    })
    return response.data
  },

  async registerComplete(credential: PublicKeyCredential): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/webauthn/register/complete', {
      id: credential.id,
      rawId: Array.from(new Uint8Array(credential.rawId)),
      response: {
        clientDataJSON: Array.from(new Uint8Array(credential.response.clientDataJSON)),
        attestationObject: Array.from(
          new Uint8Array((credential.response as AuthenticatorAttestationResponse).attestationObject)
        ),
      },
      type: credential.type,
    })
    return response.data
  },

  async loginStart(username: string): Promise<WebAuthnChallenge> {
    const response = await apiClient.post<WebAuthnChallenge>('/auth/webauthn/login/start', {
      username,
    })
    return response.data
  },

  async loginComplete(credential: PublicKeyCredential): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/webauthn/login/complete', {
      id: credential.id,
      rawId: Array.from(new Uint8Array(credential.rawId)),
      response: {
        clientDataJSON: Array.from(new Uint8Array(credential.response.clientDataJSON)),
        authenticatorData: Array.from(
          new Uint8Array((credential.response as AuthenticatorAssertionResponse).authenticatorData)
        ),
        signature: Array.from(
          new Uint8Array((credential.response as AuthenticatorAssertionResponse).signature)
        ),
        userHandle: (credential.response as AuthenticatorAssertionResponse).userHandle
          ? Array.from(
              new Uint8Array((credential.response as AuthenticatorAssertionResponse).userHandle!)
            )
          : null,
      },
      type: credential.type,
    })
    return response.data
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout')
    localStorage.removeItem('auth_token')
  },
}
