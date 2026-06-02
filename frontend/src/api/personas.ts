import { api } from './client'

export interface PersonaData {
  id?: number
  name: string
  avatar_url?: string
  description?: string
  tone?: string
  speaking_style?: string
  catchphrase?: string
  target_audience?: string
  professional_field?: string
  reference_account?: string
  forbidden_words?: string
  full_prompt?: string
  sort_order?: number
  is_active?: boolean
}

export async function listPersonas() {
  const res = await api.get('/api/personas')
  return res.data
}

export async function createPersona(data: PersonaData) {
  const res = await api.post('/api/personas', data)
  return res.data
}

export async function updatePersona(id: number, data: PersonaData) {
  const res = await api.put(`/api/personas/${id}`, data)
  return res.data
}

export async function deletePersona(id: number) {
  const res = await api.delete(`/api/personas/${id}`)
  return res.data
}
