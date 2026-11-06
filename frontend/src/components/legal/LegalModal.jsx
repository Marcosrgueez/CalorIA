import { useState } from 'react'
import { X } from 'lucide-react'

const LEGAL_CONTENT = {
  terminos: {
    title: 'Términos y Condiciones',
    lastUpdated: '2025',
    sections: [
      {
        title: '1. Objeto y aceptación',
        content: `CalorIA es una aplicación de planificación nutricional asistida por inteligencia artificial. El uso de esta aplicación implica la aceptación de los presentes términos. Si no estás de acuerdo con estos términos, no debes usar la aplicación.`,
      },
      {
        title: '2. Descripción del servicio',
        content: `CalorIA proporciona:\n- Planes nutricionales personalizados generados mediante inteligencia artificial\n- Estimaciones de precios de productos alimenticios de supermercados\n- Análisis de imágenes de alimentos mediante IA\n- Seguimiento de objetivos nutricionales y de peso\n\nEstos servicios tienen carácter informativo y orientativo.`,
      },
      {
        title: '3. Limitación de responsabilidad médica',
        content: `CalorIA NO es un servicio médico ni nutricional profesional. Los planes y recomendaciones generados son orientativos y NO sustituyen el consejo, diagnóstico o tratamiento de un profesional de la salud, médico o nutricionista titulado.\n\nEl usuario asume la responsabilidad de consultar con profesionales de la salud antes de realizar cambios significativos en su dieta, especialmente si padece alguna enfermedad, alergia o condición médica.\n\nCalorIA no se responsabiliza de daños derivados del uso de las recomendaciones nutricionales.`,
      },
      {
        title: '4. Precios y datos de supermercados',
        content: `Los precios mostrados en la aplicación son ORIENTATIVOS y han sido obtenidos de fuentes públicas disponibles en internet. Pueden no reflejar el precio actual exacto en cada establecimiento.\n\nCalorIA no tiene relación comercial con los supermercados mencionados (Mercadona, Carrefour, Gadis, Consum u otros). Las marcas y logos de dichos supermercados son propiedad de sus respectivos titulares.\n\nSiempre verifica el precio actual en la web o establecimiento del supermercado antes de realizar tu compra.`,
      },
      {
        title: '5. Uso del servicio',
        content: `El usuario se compromete a:\n- Usar la aplicación para fines personales y no comerciales\n- No intentar vulnerar la seguridad de la aplicación\n- Proporcionar información veraz en su perfil nutricional\n- No usar la aplicación si es menor de 16 años sin supervisión de un adulto`,
      },
      {
        title: '6. Propiedad intelectual',
        content: `El código, diseño, marca y contenidos propios de CalorIA están protegidos por derechos de propiedad intelectual. Queda prohibida su reproducción sin autorización expresa.`,
      },
      {
        title: '7. Modificaciones',
        content: `CalorIA se reserva el derecho de modificar estos términos en cualquier momento. Los cambios serán notificados a través de la aplicación.`,
      },
      {
        title: '8. Legislación aplicable',
        content: `Estos términos se rigen por la legislación española. Para cualquier controversia, las partes se someten a los juzgados y tribunales de España.`,
      },
    ],
  },
  privacidad: {
    title: 'Política de Privacidad',
    lastUpdated: '2025',
    sections: [
      {
        title: '1. Responsable del tratamiento',
        content: `El responsable del tratamiento de los datos personales recogidos a través de CalorIA es el titular de la aplicación, de conformidad con el Reglamento General de Protección de Datos (RGPD) y la Ley Orgánica 3/2018 de Protección de Datos Personales (LOPDGDD).`,
      },
      {
        title: '2. Datos que recopilamos',
        content: `CalorIA puede recopilar y tratar los siguientes datos:\n\nDATOS QUE TÚ PROPORCIONAS:\n- Nombre de usuario\n- Datos corporales: peso, altura, edad, sexo\n- Objetivos nutricionales y de salud\n- Fotografías de alimentos (procesadas y no almacenadas permanentemente)\n\nDATOS GENERADOS AUTOMÁTICAMENTE:\n- Datos de uso de la aplicación\n- Preferencias y configuración guardadas localmente en tu dispositivo`,
      },
      {
        title: '3. Finalidad del tratamiento',
        content: `Tus datos se usan exclusivamente para:\n- Generar planes nutricionales personalizados\n- Calcular tus necesidades calóricas y de macronutrientes\n- Mejorar las recomendaciones de la IA\n- Permitirte hacer seguimiento de tu progreso`,
      },
      {
        title: '4. Base legal',
        content: `El tratamiento de tus datos se basa en:\n- Tu consentimiento explícito al usar la aplicación\n- La ejecución del servicio que nos solicitas\n- Nuestro interés legítimo en mejorar el servicio`,
      },
      {
        title: '5. Almacenamiento de datos',
        content: `La mayoría de tus datos se almacenan LOCALMENTE en tu dispositivo (localStorage del navegador). No se transmiten a servidores externos salvo lo estrictamente necesario para:\n- Autenticación (si usas cuenta de usuario)\n- Generación de planes mediante IA (datos mínimos necesarios)\n- Consultas de precios a fuentes públicas`,
      },
      {
        title: '6. Terceros',
        content: `CalorIA utiliza los siguientes servicios de terceros:\n- Groq AI: para análisis de imágenes (imágenes procesadas temporalmente, no almacenadas)\n- OpenFoodFacts: base de datos pública de alimentos (consultas anónimas)\n\nNo vendemos ni cedemos tus datos a terceros con fines comerciales.`,
      },
      {
        title: '7. Tus derechos (RGPD)',
        content: `Tienes derecho a:\n- ACCESO: conocer qué datos tenemos sobre ti\n- RECTIFICACIÓN: corregir datos inexactos\n- SUPRESIÓN: eliminar tus datos ("derecho al olvido")\n- PORTABILIDAD: recibir tus datos en formato portable\n- OPOSICIÓN: oponerte al tratamiento de tus datos\n- LIMITACIÓN: solicitar la limitación del tratamiento\n\nPara ejercer estos derechos, usa la opción "Eliminar mis datos" en el Perfil de la app.`,
      },
      {
        title: '8. Menores de edad',
        content: `CalorIA no está dirigida a menores de 16 años. No recopilamos conscientemente datos de menores. Si eres menor de 16 años, necesitas el consentimiento de tus padres o tutores.`,
      },
      {
        title: '9. Cookies y almacenamiento local',
        content: `CalorIA usa localStorage del navegador para guardar tus preferencias y datos de perfil localmente. No usamos cookies de seguimiento ni publicidad.`,
      },
      {
        title: '10. Contacto',
        content: `Para cualquier consulta sobre privacidad o para ejercer tus derechos, puedes contactarnos a través de la aplicación en la sección de Perfil > Contacto.`,
      },
    ],
  },
  aviso: {
    title: 'Aviso Legal',
    lastUpdated: '2025',
    sections: [
      {
        title: 'Identificación',
        content: `En cumplimiento de la Ley 34/2002, de 11 de julio, de Servicios de la Sociedad de la Información y de Comercio Electrónico (LSSI-CE), se informa que CalorIA es una aplicación web desarrollada y operada por su titular.`,
      },
      {
        title: 'Propiedad intelectual',
        content: `El diseño, código fuente, textos, imágenes propias y demás elementos de CalorIA están protegidos por la legislación española e internacional sobre propiedad intelectual e industrial.\n\nLas marcas de supermercados (Mercadona, Carrefour, Gadis, Consum) son propiedad de sus respectivos titulares. CalorIA no tiene vinculación comercial con dichas empresas.\n\nLas fotografías de alimentos pueden provenir de Unsplash (licencia libre) u otras fuentes con licencia apropiada.`,
      },
      {
        title: 'Exención de responsabilidad',
        content: `CalorIA no se responsabiliza de:\n- Decisiones de salud tomadas basándose en las recomendaciones de la app\n- Variaciones en los precios de supermercados respecto a los mostrados\n- Interrupciones del servicio por causas técnicas\n- Daños derivados del uso incorrecto de la aplicación`,
      },
      {
        title: 'Legislación aplicable',
        content: `Este aviso legal se rige por la legislación española, siendo competentes los Juzgados y Tribunales españoles para resolver cualquier controversia que pudiera derivarse.`,
      },
    ],
  },
}

export default function LegalModal({ onClose, initialTab = 'terminos' }) {
  const [activeTab, setActiveTab] = useState(initialTab)
  const content = LEGAL_CONTENT[activeTab]

  return (
    <div className="fixed inset-0 z-[100] flex flex-col" style={{ background: 'var(--bg)' }}>

      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-12 pb-4 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}>
        <h1 className="text-[17px] font-bold" style={{ color: 'var(--text-1)' }}>Legal</h1>
        <button onClick={onClose}
          className="w-8 h-8 rounded-full flex items-center justify-center active:scale-[0.9] transition-transform"
          style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}>
          <X size={16} />
        </button>
      </div>

      {/* Tab switcher */}
      <div className="flex px-4 py-3 gap-2 flex-shrink-0 overflow-x-auto no-scrollbar"
        style={{ borderBottom: '1px solid var(--border)' }}>
        {[
          { id: 'terminos',   label: 'Términos' },
          { id: 'privacidad', label: 'Privacidad' },
          { id: 'aviso',      label: 'Aviso Legal' },
        ].map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className="flex-shrink-0 px-4 py-1.5 rounded-full text-[13px] font-medium transition-colors duration-150 active:scale-[0.95]"
            style={{
              background: activeTab === t.id ? 'var(--cta)' : 'var(--bg-surface2)',
              color: activeTab === t.id ? '#fff' : 'var(--text-2)',
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-5 py-4 no-scrollbar">
        <p className="text-[11px] mb-4" style={{ color: 'var(--text-3)' }}>
          Última actualización: {content.lastUpdated}
        </p>
        {content.sections.map((section, i) => (
          <div key={i} className="mb-5">
            <h2 className="text-[14px] font-bold mb-2" style={{ color: 'var(--text-1)' }}>
              {section.title}
            </h2>
            <p className="text-[13px] leading-relaxed whitespace-pre-line" style={{ color: 'var(--text-2)' }}>
              {section.content}
            </p>
          </div>
        ))}
        <div className="h-8" />
      </div>
    </div>
  )
}
