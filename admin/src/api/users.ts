import { apiClient } from './client'

export interface User {
  id: string
  username: string
  display_name: string
  email: string | null
  telegram_chat_id: string | null
  created_at: string
  updated_at: string
}

export interface UpdateUserRequest {
  display_name?: string
  email?: string
  telegram_chat_id?: string
}

export const usersApi = {
  async getProfile(): Promise<User> {
    const response = await apiClient.get<User>('/users/me')
    return response.data
  },

  async updateProfile(data: UpdateUserRequest): Promise<User> {
    const response = await apiClient.patch<User>('/users/me', data)
    return response.data
  },
}
