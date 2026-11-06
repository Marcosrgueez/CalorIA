export const ACTIVITY_LEVELS = [
  { value: 1.2,   label: 'Sedentario',  description: 'Poco o ningún ejercicio' },
  { value: 1.375, label: 'Ligero',      description: '1–3 días/semana' },
  { value: 1.55,  label: 'Moderado',    description: '3–5 días/semana' },
  { value: 1.725, label: 'Activo',      description: '6–7 días/semana' },
  { value: 1.9,   label: 'Muy activo',  description: '2× al día / trabajo físico' },
]

export const GOALS = {
  cut:      { budget: 4.5, factor: 0.80, label: 'Perder peso',   protRatio: 0.30, fatRatio: 0.25, carbMinRatio: 0.40, carbMaxRatio: 0.50 },
  maintain: { budget: 5.0, factor: 1.00, label: 'Mantener',      protRatio: 0.25, fatRatio: 0.30, carbMinRatio: 0.40, carbMaxRatio: 0.55 },
  bulk:     { budget: 7.0, factor: 1.15, label: 'Ganar músculo', protRatio: 0.35, fatRatio: 0.25, carbMinRatio: 0.40, carbMaxRatio: 0.50 },
}

export function calcBMR(sex, weight, height, age) {
  return sex === 'm'
    ? 88.362 + 13.397 * weight + 4.799 * height - 5.677 * age
    : 447.593 + 9.247 * weight + 3.098 * height - 4.330 * age
}

export function calcTDEE(sex, weight, height, age, activity) {
  return Math.round(calcBMR(sex, weight, height, age) * activity)
}

export function calcKcal(sex, weight, height, age, activity, goalFactor) {
  return Math.round(calcTDEE(sex, weight, height, age, activity) * goalFactor)
}

export function calcAutoMacros(kcal, goalKey) {
  const g = GOALS[goalKey] || GOALS.maintain
  return {
    prot:     Math.round(kcal * g.protRatio / 4),
    fat:      Math.round(kcal * g.fatRatio / 9),
    carbsMin: Math.round(kcal * g.carbMinRatio / 4),
    carbsMax: Math.round(kcal * g.carbMaxRatio / 4),
  }
}
