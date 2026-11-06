import { useState, useEffect, useCallback, useRef } from 'react'
import { calcKcal, calcAutoMacros, GOALS } from '../utils/tdee'

const PROFILE_KEY = 'mm_profile'

const DEFAULT_FITNESS = {
  enabled: false, level: 'beginner', type: 'mixed',
  days_per_week: 3, equipment: 'none',
}

const DEFAULT_PROFILE = {
  name: '', sex: 'm', age: 28, weight: 72,
  height: 175, activity: 1.55, goal: 'maintain', budget: 5.0,
  supermarket: 'mercadona',
  weight_goal: null, goal_date: null,
  fitness: DEFAULT_FITNESS,
  macros_custom: false,
  custom_prot: null, custom_fat: null,
  custom_carbs_min: null, custom_carbs_max: null,
}

export function useProfile() {
  const [profile, setProfile] = useState(() => {
    try {
      const raw = localStorage.getItem(PROFILE_KEY)
      if (raw) {
        const saved = JSON.parse(raw)
        return { ...DEFAULT_PROFILE, ...saved, fitness: { ...DEFAULT_FITNESS, ...saved.fitness } }
      }
    } catch {}
    return DEFAULT_PROFILE
  })

  const initRef = useRef(true)

  useEffect(() => {
    if (initRef.current) { initRef.current = false; return }
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile))
  }, [profile])

  const kcal = calcKcal(
    profile.sex, profile.weight, profile.height,
    profile.age, profile.activity, GOALS[profile.goal]?.factor ?? 1.0
  )

  const autoMacros = calcAutoMacros(kcal, profile.goal)

  const macros = profile.macros_custom ? {
    prot:     profile.custom_prot     ?? autoMacros.prot,
    fat:      profile.custom_fat      ?? autoMacros.fat,
    carbsMin: profile.custom_carbs_min ?? autoMacros.carbsMin,
    carbsMax: profile.custom_carbs_max ?? autoMacros.carbsMax,
  } : autoMacros

  const updateProfile = useCallback((field, value) => {
    setProfile(p => ({ ...p, [field]: value }))
  }, [])

  const resetProfile = useCallback(() => {
    setProfile(DEFAULT_PROFILE)
    localStorage.removeItem(PROFILE_KEY)
  }, [])

  function buildPayload(prefs) {
    const goalFactor = GOALS[profile.goal]?.factor ?? 1.0
    const base = calcKcal(profile.sex, profile.weight, profile.height, profile.age, profile.activity, goalFactor)
    const fitness = profile.fitness ?? DEFAULT_FITNESS
    let burnPerDay = 0
    if (fitness.enabled) {
      const KCAL_BURN = {
        cardio:   { beginner: 250, intermediate: 350, advanced: 450 },
        strength: { beginner: 200, intermediate: 280, advanced: 350 },
        mixed:    { beginner: 300, intermediate: 400, advanced: 500 },
        yoga:     { beginner: 150, intermediate: 200, advanced: 250 },
      }
      const sessKcal = KCAL_BURN[fitness.type]?.[fitness.level] ?? 0
      burnPerDay = Math.round((sessKcal * fitness.days_per_week) / 7)
    }
    const finalKcal = base + burnPerDay

    return {
      name:          profile.name || 'Usuario',
      kcal_target:   finalKcal,
      min_protein_g: macros.prot,
      max_fat_g:     macros.fat,
      min_carbs_g:   macros.carbsMin,
      max_carbs_g:   macros.carbsMax,
      budget_eur:    profile.budget,
      supermarket:   profile.supermarket ?? 'mercadona',
      ...(prefs ? { preferences: prefs } : {}),
    }
  }

  const goalLabel = GOALS[profile.goal]?.label ?? 'Mantener'

  return {
    profile, updateProfile, resetProfile,
    macros, kcal, goalLabel, buildPayload,
  }
}
