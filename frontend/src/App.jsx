import { useState } from 'react'
import { useTheme } from './hooks/useTheme'
import { useProfile } from './hooks/useProfile'
import { useAuth } from './hooks/useAuth'
import { useDiet } from './hooks/useDiet'
import BottomNav from './components/layout/BottomNav'
import TabInicio from './tabs/TabInicio'
import TabPlan from './tabs/TabPlan'
import TabCamara from './tabs/TabCamara'
import TabStats from './tabs/TabStats'
import TabChat from './tabs/TabChat'
import TabPerfil from './tabs/TabPerfil'
import OnboardingConsent from './components/legal/OnboardingConsent'

const CONSENT_KEY = 'mm_consent_accepted'

export default function App() {
  const { theme, toggle: toggleTheme } = useTheme()
  const profileState = useProfile()
  const authState = useAuth()
  const dietState = useDiet()
  const [tab, setTab] = useState('inicio')
  const [consentAccepted, setConsentAccepted] = useState(
    () => localStorage.getItem(CONSENT_KEY) === '1'
  )

  function handleAcceptConsent() {
    localStorage.setItem(CONSENT_KEY, '1')
    setConsentAccepted(true)
  }

  const shared = { theme, toggleTheme, profileState, authState }

  return (
    <div className="app-shell flex flex-col" style={{ height: '100dvh', background: 'var(--bg)', color: 'var(--text-1)' }}>
      <main className="flex-1 overflow-y-auto overflow-x-hidden no-scrollbar">
        {tab === 'inicio'  && <TabInicio  {...shared} setTab={setTab} />}
        {tab === 'plan'    && <TabPlan    {...shared} dietState={dietState} />}
        {tab === 'camara'  && <TabCamara  {...shared} />}
        {tab === 'stats'   && <TabStats   {...shared} />}
        {tab === 'chat'    && <TabChat    {...shared} dietState={dietState} />}
        {tab === 'perfil'  && <TabPerfil  {...shared} />}
      </main>
      <BottomNav active={tab} onChange={setTab} />
      {!consentAccepted && <OnboardingConsent onAccept={handleAcceptConsent} />}
    </div>
  )
}
