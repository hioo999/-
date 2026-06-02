import { api, setAuthToken } from './client'

export { setAuthToken }

export interface AuthUser {
  id: number
  name: string
  email: string
  is_admin?: boolean
  is_active?: boolean
}

export interface AuthSessionResponse {
  token: string
  user: AuthUser
}

export async function registerAccount(params: { name: string; email: string; password: string }): Promise<{ code: number; data: AuthSessionResponse }> {
  const res = await api.post('/api/auth/register', params)
  return res.data
}

export async function loginAccount(params: { email: string; password: string }): Promise<{ code: number; data: AuthSessionResponse }> {
  const res = await api.post('/api/auth/login', params)
  return res.data
}

export async function logoutAccount(): Promise<{ code: number; message: string }> {
  const res = await api.post('/api/auth/logout')
  return res.data
}

export async function getCurrentAccount(): Promise<{ code: number; data: { user: AuthUser } }> {
  const res = await api.get('/api/auth/me')
  return res.data
}
