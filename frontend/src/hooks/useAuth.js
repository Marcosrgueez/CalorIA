import { useState, useCallback } from 'react'
import * as api from '../api/client'

const TOKEN_KEY = 'mm_token'
const AUTH_KEY  = 'mm_auth'
const DIETS_KEY = 'mm_diets_today'

function decodeToken(token) {
  try { return JSON.parse(atob(token.split('.')[1])) } catch { return null }
}

function loadAuth() {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return null
    const payload = decodeToken(token)
    if (!payload || payload.exp * 1000 < Date.now()) {
      localStorage.removeItem(TOKEN_KEY)
      return null
    }
    const stored = localStorage.getItem(AUTH_KEY)
    return stored ? JSON.parse(stored) : { username: payload.username, plan: payload.plan, diets_today: 0 }
  } catch { return null }
}

function loadDietsToday() {
  try {
    const raw = localStorage.getItem(DIETS_KEY)
    if (!raw) return 0
    const { date, count } = JSON.parse(raw)
    return date === new Date().toISOString().slice(0, 10) ? count : 0
  } catch { return 0 }
}

function saveDietsToday(count) {
  localStorage.setItem(DIETS_KEY, JSON.stringify({ date: new Date().toISOString().slice(0, 10), count }))
}

export function useAuth() {
  const [auth, setAuth] = useState(loadAuth)
  const [dietsToday, setDietsToday] = useState(loadDietsToday)

  const isPremium = auth?.plan === 'premium'
  const FREE_LIMIT = 3

  function _applySession(data) {
    localStorage.setItem(TOKEN_KEY, data.access_token)
    const info = { username: data.username, plan: data.plan, diets_today: data.diets_today }
    localStorage.setItem(AUTH_KEY, JSON.stringify(info))
    setAuth(info)
    if (data.plan !== 'premium') {
      setDietsToday(data.diets_today ?? 0)
      saveDietsToday(data.diets_today ?? 0)
    }
  }

  const login = useCallback(async (email, password) => {
    const res = await api.login({ email, password })
    _applySession(res.data)
  }, [])

  const register = useCallback(async (username, email, password) => {
    const res = await api.register({ username, email, password })
    _applySession(res.data)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(AUTH_KEY)
    localStorage.removeItem(DIETS_KEY)
    setAuth(null)
    setDietsToday(0)
  }, [])

  const incrementDiets = useCallback(() => {
    if (isPremium) return
    setDietsToday(n => { const next = n + 1; saveDietsToday(next); return next })
  }, [isPremium])

  return { auth, isPremium, dietsToday, freeLimit: FREE_LIMIT, login, register, logout, incrementDiets }
}
