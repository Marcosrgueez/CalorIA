import { useState } from 'react'
import * as api from '../api/client'

const DIET_CACHE_KEY = 'mm_last_diet'
const WEEK_CACHE_KEY = 'mm_last_week'

function readCache(key) {
  try { return JSON.parse(localStorage.getItem(key)) } catch { return null }
}

export function useDiet() {
  const [diet, setDietState] = useState(() => readCache(DIET_CACHE_KEY))
  const [weekPlan, setWeekPlanState] = useState(() => readCache(WEEK_CACHE_KEY))
  const [loading, setLoading] = useState({ today: false, week: false, fridge: false, shopping: false })
  const [error, setError] = useState(null)

  function setDiet(d) {
    setDietState(d)
    if (d) localStorage.setItem(DIET_CACHE_KEY, JSON.stringify(d))
    else localStorage.removeItem(DIET_CACHE_KEY)
  }

  function setWeekPlan(w) {
    setWeekPlanState(w)
    if (w) localStorage.setItem(WEEK_CACHE_KEY, JSON.stringify(w))
    else localStorage.removeItem(WEEK_CACHE_KEY)
  }

  function setLoad(key, val) { setLoading(l => ({ ...l, [key]: val })) }

  async function generateToday(payload) {
    setLoad('today', true)
    setError(null)
    try {
      const res = await api.generateDietRecipe(payload)
      setDiet(res.data)        // persiste en localStorage
      return res.data
    } catch (e) {
      const detail = e.response?.data?.detail
      const msg = (typeof detail === 'object' && detail?.message) ? detail.message : String(detail ?? 'Error generando dieta')
      const sugs = (typeof detail === 'object' && detail?.suggestions) ? detail.suggestions : []
      setError({ message: msg, suggestions: sugs, code: detail?.code })
      throw e
    } finally {
      setLoad('today', false)
    }
  }

  async function generateWeek(payload) {
    setLoad('week', true)
    setError(null)
    try {
      const res = await api.generateWeekRecipe(payload)
      setWeekPlan(res.data)    // persiste en localStorage
      return res.data
    } catch (e) {
      const detail = e.response?.data?.detail
      const msg = (typeof detail === 'object' && detail?.message) ? detail.message : String(detail ?? 'Error generando plan semanal')
      setError({ message: msg, suggestions: detail?.suggestions ?? [], code: detail?.code })
      throw e
    } finally {
      setLoad('week', false)
    }
  }

  async function generateFridge(payload) {
    setLoad('fridge', true)
    setError(null)
    try {
      const res = await api.generateFridgeDiet(payload)
      setDiet(res.data)        // persiste en localStorage
      return res.data
    } catch (e) {
      const detail = e.response?.data?.detail
      const msg = (typeof detail === 'object' && detail?.message) ? detail.message : String(detail ?? 'Error generando dieta')
      setError({ message: msg, suggestions: detail?.suggestions ?? [], code: detail?.code })
      throw e
    } finally {
      setLoad('fridge', false)
    }
  }

  async function generateShopping(weekData) {
    setLoad('shopping', true)
    try {
      const res = await api.generateShopping(weekData)
      return res.data
    } finally {
      setLoad('shopping', false)
    }
  }

  async function swapMeal(dietId, mealName, payload) {
    try {
      const res = await api.swapMeal(dietId, mealName, payload)
      return res.data
    } catch (e) {
      const detail = e.response?.data?.detail
      const msg = (typeof detail === 'object' && detail?.message) ? detail.message : String(detail ?? 'Error al cambiar comida')
      setError({ message: msg, suggestions: [], code: detail?.code })
      throw e
    }
  }

  function clearError() { setError(null) }

  function clearDiet() { setDiet(null); setWeekPlan(null) }

  return { diet, weekPlan, loading, error, generateToday, generateWeek, generateFridge, generateShopping, swapMeal, setDiet, setWeekPlan, clearDiet, clearError }
}
