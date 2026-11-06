import axios from 'axios'

const TOKEN_KEY = 'mm_token'
const baseURL = import.meta.env.VITE_API_URL || ''

const api = axios.create({ baseURL })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export const login    = (data) => api.post('/auth/login',    data)
export const register = (data) => api.post('/auth/register', data)
export const getMe    = ()     => api.get('/auth/me')

export const generateDietRecipe = (data) => api.post('/diet/recipe',          data)
export const generateWeekRecipe = (data) => api.post('/diet/week/recipe',     data)
export const generateFridgeDiet = (data) => api.post('/diet/fridge',          data)
export const generateShopping   = (data) => api.post('/diet/week/shopping-list', data)

export const fetchDiets    = (limit = 20) => api.get(`/diets?limit=${limit}`)
export const fetchDietById = (id)         => api.get(`/diets/${id}`)
export const rateDiet      = (id, rating) => api.post(`/diets/${id}/rate?rating=${rating}`)

export const getProducts          = ()         => api.get('/products')
export const fetchCatalogStats    = ()         => api.get('/products/stats')
export const compareProduct       = (keyword)  => api.get(`/products/compare?keyword=${encodeURIComponent(keyword)}`)
export const compareProductsBatch = (keywords) => api.post('/products/compare-batch', keywords)

export const swapMeal = (dietId, mealName, payload) =>
  api.post(`/diet/${dietId}/meal/${encodeURIComponent(mealName)}/swap`, payload)

export const scanBarcode = (barcode)  => api.post(`/scan/barcode?barcode=${encodeURIComponent(barcode)}`)
export const scanPhoto   = (formData) => api.post('/scan/photo',  formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const scanLabel   = (formData) => api.post('/scan/label',  formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const scanFridge  = (formData) => api.post('/scan/fridge', formData, { headers: { 'Content-Type': 'multipart/form-data' } })

export const sendChat = (data) => api.post('/api/chat', data)
