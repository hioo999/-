import axios from 'axios'

export const apiBaseURL = import.meta.env.VITE_API_BASE_URL || ''

export const api = axios.create({
  baseURL: apiBaseURL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

let authToken = ''

api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`
  }
  return config
})

export function setAuthToken(token: string) {
  authToken = token
}
