import { StrictMode, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { api, iniciarSesion, type Estado, type Lista, type Producto } from './api'
import './estilos.css'

const DISCIPLINAS = [
  { id: 'running', nombre: 'Running', texto: 'Correr en calle, pista o montaña', icono: '🏃' },
  { id: 'ciclismo', nombre: 'Ciclismo', texto: 'Ruta, montaña o ciudad', icono: '🚴' },
  { id: 'entrenamiento', nombre: 'Entrenamiento', texto: 'Gimnasio, fuerza, yoga y cardio', icono: '🏋️' },
]
const TIPOS = [
  { id: 'ropa', nombre: 'Ropa', texto: 'Prendas y calzado' },
  { id: 'accesorios', nombre: 'Accesorios', texto: 'Luces, bolsos, hidratación, relojes' },
  { id: 'proteccion', nombre: 'Protección', texto: 'Cascos, guantes, rodilleras' },
  { id: 'equipamiento', nombre: 'Equipamiento', texto: 'Equipos, partes y herramientas' },
]
const NOMBRE: Record<string, string> = Object.fromEntries([...DISCIPLINAS, ...TIPOS].map(x => [x.id, x.nombre]))
const MAX = 5
// Versión en español validada del System Usability Scale (Sevilla-González et al., 2020, JMIR Human Factors, CC BY 4.0).
// Texto sin modificar; todas las preguntas son obligatorias y no admiten "No puedo evaluar".
const SUS = [
  'Me gustaría usar esta herramienta frecuentemente.',
  'Considero que esta herramienta es innecesariamente compleja',
  'Considero que la herramienta es fácil de usar.',
  'Considero necesario el apoyo de personal experto para poder utilizar esta herramienta',
  'Considero que las funciones de la herramienta están bien integradas',
  'Considero que la herramienta presenta muchas contradicciones',
  'Imagino que la mayoría de las personas aprenderían a usar esta herramienta rápidamente',
  'Considero que el uso de esta herramienta es tedioso',
  'Me sentí muy confiado al usar la herramienta',
  'Necesité saber bastantes cosas antes de poder empezar a usar esta herramienta',
]
const PREGUNTAS = [
  ['intereses', 'Entendí para qué se pedían mis intereses.'],
  ['expresar', 'Pude expresar mis intereses con las opciones disponibles.'],
  ['comprar', 'Entendí que marcar un producto no significa comprarlo.'],
  ['explicacion', 'Comprendí por qué me recomendaron al menos un producto.'],
  ['cambiar', 'Encontré cómo cambiar mis preferencias.'],
  ['pasos', 'La cantidad de pasos me pareció razonable.'],
]

type Paso = 'inicio' | 'participar' | 'deportes' | 'tipos' | 'gustos' | 'recomendaciones' | 'evaluar' | 'gracias'

function Imagen({ p }: { p: Producto }) {
  const [error, setError] = useState(false)
  if (!p.imagen || error) return <div className="sin-imagen">{DISCIPLINAS.find(d => d.id === p.disciplina)?.icono}<span>{p.categoria_es}</span></div>
  return <img src={p.imagen} alt={p.nombre} loading="lazy" referrerPolicy="no-referrer" onError={() => setError(true)} />
}

function Tarjeta({ p, children, marcado }: { p: Producto; children?: React.ReactNode; marcado?: boolean }) {
  return (
    <article className={'tarjeta' + (marcado ? ' marcada' : '')}>
      <div className="foto"><Imagen p={p} /></div>
      <div className="cuerpo">
        <p className="categoria">{p.categoria_es} · {NOMBRE[p.disciplina]}</p>
        <h3 title={p.nombre}>{p.nombre}</h3>
        {p.marca && <p className="marca">{p.marca}</p>}
        {children}
      </div>
    </article>
  )
}

function Pasos({ paso, ir }: { paso: Paso; ir: (p: Paso) => void }) {
  const orden: [Paso, string][] = [['deportes', 'Deportes'], ['tipos', 'Tipo'], ['gustos', 'Tus gustos'], ['recomendaciones', 'Para ti']]
  const actual = orden.findIndex(o => o[0] === paso)
  if (actual < 0) return null
  return (
    <nav className="pasos" aria-label="Pasos">
      {orden.map(([id, t], i) => (
        <button key={id} className={i === actual ? 'activo' : i < actual ? 'hecho' : ''} disabled={i > actual} onClick={() => ir(id)}>
          <b>{i + 1}</b> {t}
        </button>
      ))}
    </nav>
  )
}

function App() {
  const [estado, setEstado] = useState<Estado | null>(null)
  const [paso, setPaso] = useState<Paso>('inicio')
  const [disc, setDisc] = useState<string[]>([])
  const [tipos, setTipos] = useState<string[]>([])
  const [sel, setSel] = useState<Producto[]>([])
  const [lista, setLista] = useState<Lista | null>(null)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)
  const [conteoTipos, setConteoTipos] = useState<Record<string, number>>({})

  useEffect(() => {
    iniciarSesion().then(e => { setEstado(e); setDisc(e.disciplinas); setTipos(e.tipos); setSel(e.selecciones) })
      .catch(e => setError(e.message))
    api<{ conteo_tipos: Record<string, number> }>('/vocabulario').then(v => setConteoTipos(v.conteo_tipos)).catch(() => {})
  }, [])

  async function accion(f: () => Promise<void>) {
    setError(''); setCargando(true)
    try { await f() } catch (e) { setError((e as Error).message) } finally { setCargando(false) }
  }
  async function guardar() {
    const e = await api<Estado>('/perfil', 'PUT', { disciplinas: disc, tipos, selecciones: sel.map(p => p.id), version: estado!.version })
    setEstado(e)
    return e
  }
  const verRecomendaciones = () => accion(async () => {
    await guardar()
    setLista(await api<Lista>('/recomendaciones'))
    setPaso('recomendaciones'); window.scrollTo(0, 0)
  })
  const reiniciar = () => accion(async () => {
    const e = await api<Estado>('/perfil', 'DELETE'); setEstado(e); setDisc([]); setTipos([]); setSel([]); setLista(null); setPaso('deportes')
  })
  const nuevaPersona = () => accion(async () => {
    const e = await api<Estado>('/sesiones', 'POST')  // sesión nueva: reemplaza la cookie de este navegador
    setEstado(e); setDisc([]); setTipos([]); setSel([]); setLista(null); setPaso('inicio'); window.scrollTo(0, 0)
  })
  const alternar = <T,>(xs: T[], x: T) => xs.includes(x) ? xs.filter(y => y !== x) : [...xs, x]

  if (!estado) return <main className="centro">{error ? <p className="error">{error}</p> : <p>Cargando Gearly… (la primera vez puede tardar un minuto)</p>}</main>

  return (
    <>
      <header className="cabecera">
        <button className="logo" onClick={() => setPaso('inicio')}>Gearly</button>
        <Pasos paso={paso} ir={setPaso} />
        <span className="codigo" title="Con este código puedes retomar tu perfil durante 7 días">
          {estado.participacion?.estado === 'activa' && <b className="insignia">Participante {estado.participacion.codigo}</b>} Tu código: <b>{estado.codigo}</b>
        </span>
      </header>
      {error && <p className="error" role="alert">{error}</p>}
      <main>
        {paso === 'inicio' && <Inicio nuevaPersona={nuevaPersona} estado={estado} continuar={() => setPaso('deportes')} evaluar={() => setPaso('participar')} retomado={e => { setEstado(e); setDisc(e.disciplinas); setTipos(e.tipos); setSel(e.selecciones) }} retirado={() => setEstado({ ...estado, participacion: estado.participacion && { ...estado.participacion, estado: 'retirada' } })} />}
        {paso === 'participar' && <Participar listo={part => { setEstado({ ...estado, participacion: part }); if (part?.estado === 'activa') setPaso('deportes') }} />}

        {paso === 'deportes' && (
          <section>
            <h1>¿Qué deportes practicas o te interesan?</h1>
            <p className="ayuda">Elige uno o varios. Esto nos ayuda a mostrarte productos de tu deporte. Puedes cambiarlo después.</p>
            <div className="opciones">
              {DISCIPLINAS.map(d => (
                <button key={d.id} className={'opcion' + (disc.includes(d.id) ? ' activa' : '')} aria-pressed={disc.includes(d.id)} onClick={() => setDisc(alternar(disc, d.id))}>
                  <span className="icono">{d.icono}</span><b>{d.nombre}</b><span>{d.texto}</span>
                </button>
              ))}
            </div>
            <Barra>
              <span>{disc.length ? `${disc.length} elegido(s)` : 'Puedes continuar sin elegir'}</span>
              <button className="principal" onClick={() => setPaso('tipos')}>Continuar →</button>
            </Barra>
          </section>
        )}

        {paso === 'tipos' && (
          <section>
            <h1>¿Qué tipo de producto buscas?</h1>
            <p className="ayuda">Opcional. Si no tienes preferencia, continúa.</p>
            <div className="opciones">
              {TIPOS.filter(t => conteoTipos[t.id] !== 0).map(t => (
                <button key={t.id} className={'opcion' + (tipos.includes(t.id) ? ' activa' : '')} aria-pressed={tipos.includes(t.id)} onClick={() => setTipos(alternar(tipos, t.id))}>
                  <b>{t.nombre}</b><span>{t.texto}</span>
                </button>
              ))}
            </div>
            <Barra>
              <button onClick={() => setPaso('deportes')}>← Atrás</button>
              <button className="principal" onClick={() => setPaso('gustos')}>Continuar →</button>
            </Barra>
          </section>
        )}

        {paso === 'gustos' && <Gustos conteo={conteoTipos} disc={disc} tipos={tipos} sel={sel} setSel={setSel} atras={() => setPaso('tipos')} ver={verRecomendaciones} cargando={cargando} />}

        {paso === 'recomendaciones' && lista && (
          <section>
            <div className="titulo-fila">
              <div>
                <h1>Elegido para ti</h1>
                <p className="ayuda">Según {disc.length ? disc.map(d => NOMBRE[d]).join(', ') : 'tus gustos'}{sel.length ? ` y los ${sel.length} productos que marcaste` : ''}. Estos son productos diferentes a los que marcaste. Nada se compra aquí.</p>
              </div>
              <div className="acciones">
                <button onClick={() => setPaso('gustos')}>✎ Cambiar mis gustos</button>
                <button onClick={reiniciar}>Empezar de nuevo</button>
                {estado.participacion?.estado === 'activa' && <button className="principal" onClick={() => setPaso('evaluar')}>Evaluar estas sugerencias</button>}
              </div>
            </div>
            {lista.motivo_alternativa && <p className="aviso">{lista.motivo_alternativa}</p>}
            <div className="rejilla">
              {lista.resultados.map((r, i) => (
                <Tarjeta key={r.producto.id} p={r.producto}>
                  <p className="numero">Recomendación {i + 1}</p>
                  <p className="porque">💡 {r.explicacion}</p>
                </Tarjeta>
              ))}
            </div>
          </section>
        )}

        {paso === 'evaluar' && <Evaluar estado={estado} terminar={() => setPaso('gracias')} irAPerfil={() => setPaso('deportes')} />}
        {paso === 'gracias' && (
          <section className="centro">
            <h1>¡Gracias por participar!</h1>
            <p>Tus respuestas quedaron guardadas con tu código de participante. Ya puedes cerrar esta página.</p>
            <p className="nota">Si cambias de opinión, puedes retirar tus respuestas durante 7 días: entra a Gearly, usa «¿Ya tienes un código?» con <b>{estado.codigo}</b> y pulsa «Retirar mis respuestas».</p>
            <Retiro alRetirar={() => setEstado({ ...estado, participacion: estado.participacion && { ...estado.participacion, estado: 'retirada' } })} />
            <p className="nota">Si otra persona va a participar en este mismo dispositivo, pulsa:</p>
            <button className="principal" onClick={nuevaPersona}>Soy otra persona: empezar de cero</button>
          </section>
        )}
      </main>
      <footer>Prototipo académico · Universidad Manuela Beltrán · Datos de productos: Amazon Reviews 2023 (McAuley Lab). No es una tienda.</footer>
    </>
  )
}

function Barra({ children }: { children: React.ReactNode }) {
  return <div className="barra">{children}</div>
}

function Retiro({ alRetirar }: { alRetirar: () => void }) {
  const [confirmar, setConfirmar] = useState(false)
  const [msg, setMsg] = useState('')
  if (msg) return <p className="aviso">{msg}</p>
  if (!confirmar) return <button onClick={() => setConfirmar(true)}>Retirar mis respuestas</button>
  return (
    <div className="aviso">
      <p>Se borrarán tus valoraciones y respuestas del estudio. Solo quedará constancia de que te retiraste. ¿Continuar?</p>
      <div className="fila">
        <button className="principal" onClick={async () => {
          try { await api('/participacion/retiro', 'POST'); alRetirar(); setMsg('Listo: tus respuestas fueron retiradas del estudio.') } catch (e) { setMsg((e as Error).message) }
        }}>Sí, retirar</button>
        <button onClick={() => setConfirmar(false)}>Cancelar</button>
      </div>
    </div>
  )
}

const H01 = [
  { k: 'q4_relacion', t: '¿Qué relación tienes con el equipo de Gearly?', o: [['companero_umb', 'Compañero/a de la UMB'], ['amigo', 'Amigo/a'], ['familiar', 'Familiar'], ['otro', 'Otra']], obligatoria: true },
  { k: 'q5_interes_actividad', t: '¿Te interesa al menos una de estas actividades: running, ciclismo o entrenamiento?', o: [['si', 'Sí'], ['no', 'No'], ['no_seguro', 'No estoy seguro']], obligatoria: true },
  { k: 'q6_edad', t: '¿En qué rango de edad te encuentras? (opcional)', o: [['18_24', '18 a 24'], ['25_34', '25 a 34'], ['35_44', '35 a 44'], ['45_mas', '45 o más'], ['prefiero_no', 'Prefiero no responder']], obligatoria: false },
  { k: 'q7_frecuencia_catalogos', t: '¿Con qué frecuencia consultas catálogos de productos por internet? (opcional)', o: [['varias_semana', 'Varias veces por semana'], ['una_semana', 'Aproximadamente una vez por semana'], ['algunas_mes', 'Algunas veces al mes'], ['menos', 'Con menor frecuencia'], ['nunca', 'Nunca'], ['prefiero_no', 'Prefiero no responder']], obligatoria: false },
  { k: 'q8_uso_previo', t: '¿Habías utilizado antes este prototipo de Gearly?', o: [['no', 'No'], ['si_piloto', 'Sí, en un piloto'], ['si_otra', 'Sí, en otra ocasión']], obligatoria: true },
  { k: 'q9_dispositivo', t: '¿Qué dispositivo estás utilizando?', o: [['movil', 'Teléfono móvil'], ['computador', 'Computador'], ['tableta', 'Tableta'], ['otro', 'Otro']], obligatoria: true },
] as const

function navegador() {
  const u = navigator.userAgent
  return /Edg\//.test(u) ? 'Edge' : /OPR\//.test(u) ? 'Opera' : /Chrome\//.test(u) ? 'Chrome' : /Firefox\//.test(u) ? 'Firefox' : /Safari\//.test(u) ? 'Safari' : 'Otro'
}

function Participar({ listo }: { listo: (p: Estado['participacion']) => void }) {
  const [acepta, setAcepta] = useState<boolean | null>(null)
  const [codigo, setCodigo] = useState('')
  const [h, setH] = useState<Record<string, string | null>>({ q6_edad: null, q7_frecuencia_catalogos: null })
  const [fin, setFin] = useState('')
  const [error, setError] = useState('')
  const completo = acepta === false || (acepta && /^[A-Za-z0-9-]{2,20}$/.test(codigo.trim()) && H01.filter(q => q.obligatoria).every(q => h[q.k]))
  if (fin) return <section className="estrecha centro"><h1>Gracias</h1><p>{fin}</p></section>
  return (
    <section className="estrecha">
      <h1>Evaluación académica de Gearly</h1>
      <div className="consentimiento">
        <p>Se te invita a participar en una evaluación académica de Gearly, un prototipo que recomienda productos deportivos. Queremos observar si sus instrucciones son comprensibles y qué tan pertinentes te parecen sus sugerencias. Se evalúa el sistema, no tus conocimientos ni tu capacidad. La sesión dura aproximadamente treinta minutos y no incluye compras ni pagos.</p>
        <p>Participar es voluntario. Puedes omitir preguntas opcionales o terminar la sesión sin consecuencias académicas. Registraremos tus intereses seleccionados, las tareas realizadas y tus valoraciones mediante un código. No se solicitarán credenciales de otras plataformas. Los resultados se presentarán de forma agregada o con comentarios sin datos que permitan identificarte.</p>
        <p>El riesgo principal es una eventual exposición de la información recogida; se limitará mediante acceso restringido, minimización de datos y separación de contactos. No se promete beneficio económico ni una recomendación perfecta. Puedes solicitar retiro mediante tu código mientras los registros puedan localizarse y antes de su anonimización irreversible.</p>
        <p>No se grabarán audio, video o pantalla. Aceptar investigación no autoriza publicidad, seguimiento comercial ni reutilización libre de tus respuestas. Tratamiento de datos conforme a la Ley 1581 de 2012.</p>
      </div>
      <fieldset className="pregunta"><legend>He leído la información, tengo dieciocho años o más y acepto participar voluntariamente.</legend>
        <button className={acepta === true ? 'activo' : ''} onClick={() => setAcepta(true)}>Sí acepto</button>
        <button className={acepta === false ? 'activo' : ''} onClick={() => setAcepta(false)}>No acepto</button>
      </fieldset>
      {acepta && (
        <>
          <label>Código de participante que te dio el equipo <input value={codigo} onChange={e => setCodigo(e.target.value)} placeholder="P001" /></label>
          {H01.map(q => (
            <fieldset key={q.k} className="pregunta"><legend>{q.t}</legend>
              {q.o.map(([v, t]) => <button key={v} className={h[q.k] === v ? 'activo' : ''} aria-pressed={h[q.k] === v} onClick={() => setH({ ...h, [q.k]: v })}>{t}</button>)}
            </fieldset>
          ))}
        </>
      )}
      {error && <p className="error">{error}</p>}
      <button className="principal" disabled={!completo} onClick={async () => {
        setError('')
        try {
          const r = await api<{ estado: string; codigo?: string }>('/participacion', 'POST', {
            codigo_participante: codigo.trim() || 'NA', acepta: !!acepta, h01: acepta ? h : {},
            tecnico: { navegador: navegador(), ancho_pantalla: window.innerWidth, alto_pantalla: window.innerHeight },
          })
          if (r.estado === 'no_acepta') setFin('No se guardó ninguna respuesta. Puedes cerrar esta página o explorar Gearly libremente.')
          else if (r.estado === 'excluida') { listo({ codigo: r.codigo!, estado: 'excluida' }); setFin('Gracias por tu interés. Esta evaluación es para personas interesadas en running, ciclismo o entrenamiento. Puedes explorar Gearly libremente.') }
          else listo({ codigo: r.codigo!, estado: 'activa' })
        } catch (e) { setError((e as Error).message) }
      }}>{acepta === false ? 'Salir' : 'Continuar a Gearly →'}</button>
    </section>
  )
}

function Inicio({ nuevaPersona, estado, continuar, evaluar, retomado, retirado }: { nuevaPersona: () => void; estado: Estado; continuar: () => void; evaluar: () => void; retomado: (e: Estado) => void; retirado: () => void }) {
  const [codigo, setCodigo] = useState('')
  const [msg, setMsg] = useState('')
  return (
    <section className="inicio">
      <h1>Encuentra productos deportivos que encajan contigo</h1>
      <p className="ayuda">Gearly es un prototipo de un trabajo de grado. Le dices qué deportes te interesan y marcas hasta {MAX} productos que te gusten, y te recomienda otros, explicando por qué.</p>
      <ol className="como">
        <li>Elige tus deportes.</li>
        <li>Di qué tipo de producto buscas (opcional).</li>
        <li>Marca hasta {MAX} productos que te gusten (opcional).</li>
        <li>Mira tus recomendaciones y por qué aparecen.</li>
      </ol>
      <p className="nota">No pedimos nombre ni correo. No se vende nada. Los nombres de los productos están en inglés porque vienen de datos públicos de Amazon; mostramos la categoría en español.</p>
      <div className="fila">
        <button className="principal" onClick={continuar}>Comenzar →</button>
        {(!estado.participacion || estado.participacion.estado === 'excluida') && <button onClick={evaluar}>Participar en la evaluación</button>}
      </div>
      {estado.participacion?.estado === 'activa' && <div className="aviso"><p>Estás participando en la evaluación con el código <b>{estado.participacion.codigo}</b>.</p><Retiro alRetirar={retirado} /></div>}
      {estado.participacion && <p><button onClick={nuevaPersona}>Soy otra persona: empezar de cero</button></p>}
      <details>
        <summary>¿Ya tienes un código de sesión (G-…)?</summary>
        <form className="fila" onSubmit={async e => {
          e.preventDefault(); setMsg('')
          if (/^\s*P\d+\s*$/i.test(codigo)) { setMsg('Ese es tu código de participante. Escríbelo dentro de «Participar en la evaluación». Aquí va el código de sesión que empieza por G- (lo ves arriba a la derecha).'); return }
          try { retomado(await api<Estado>('/sesiones/retomar', 'POST', { codigo })); setMsg('Perfil recuperado.') } catch (err) { setMsg((err as Error).message) }
        }}>
          <input value={codigo} onChange={e => setCodigo(e.target.value)} placeholder="G-XXXXXX" aria-label="Código" />
          <button>Retomar</button>
        </form>
        {msg && <p>{msg}</p>}
      </details>
    </section>
  )
}

function Gustos({ conteo, disc, tipos, sel, setSel, atras, ver, cargando }: {
  conteo: Record<string, number>; disc: string[]; tipos: string[]; sel: Producto[]; setSel: (p: Producto[]) => void; atras: () => void; ver: () => void; cargando: boolean
}) {
  const [q, setQ] = useState('')
  const [fd, setFd] = useState<string[]>(disc)
  const [ft, setFt] = useState<string[]>(tipos)
  const [pagina, setPagina] = useState(1)
  const [items, setItems] = useState<Producto[]>([])
  const [total, setTotal] = useState(0)
  const [parecidos, setParecidos] = useState<{ de: Producto; productos: Producto[] } | null>(null)
  const ids = useMemo(() => new Set(sel.map(p => p.id)), [sel])

  useEffect(() => {
    const t = setTimeout(() => {
      const ps = new URLSearchParams({ q, disciplina: fd.join(','), tipo: ft.join(','), pagina: String(pagina), limite: '24' })
      api<{ total: number; productos: Producto[] }>('/productos?' + ps).then(r => { setTotal(r.total); setItems(pagina === 1 ? r.productos : prev => [...prev, ...r.productos]) })
    }, 250)
    return () => clearTimeout(t)
  }, [q, fd, ft, pagina])
  useEffect(() => setPagina(1), [q, fd, ft])

  async function marcar(p: Producto) {
    if (ids.has(p.id)) { setSel(sel.filter(x => x.id !== p.id)); return }
    if (sel.length >= MAX) return
    const nuevos = [...sel, p]
    setSel(nuevos)
    const r = await api<{ productos: Producto[] }>(`/parecidos?de=${p.id}&excluir=${nuevos.map(x => x.id).join(',')}`).catch(() => null)
    if (r?.productos.length) setParecidos({ de: p, productos: r.productos })
  }
  const filtro = (xs: string[], set: (v: string[]) => void, x: string) => set(xs.includes(x) ? xs.filter(y => y !== x) : [...xs, x])
  const Boton = ({ p }: { p: Producto }) => (
    <button className={ids.has(p.id) ? 'me-gusta activo' : 'me-gusta'} disabled={!ids.has(p.id) && sel.length >= MAX} onClick={() => marcar(p)} aria-pressed={ids.has(p.id)}>
      {ids.has(p.id) ? '♥ Te gusta' : '♡ Me gusta'}
    </button>
  )
  return (
    <section>
      <h1>Marca lo que te gusta</h1>
      <p className="ayuda">Marca hasta {MAX} productos que te llamen la atención. Es opcional: si no marcas ninguno, recomendamos según tus deportes.</p>
      <div className="filtros">
        <input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar (en inglés o por categoría): casco, light, yoga…" aria-label="Buscar productos" />
        <div className="chips">
          {DISCIPLINAS.map(d => <button key={d.id} className={fd.includes(d.id) ? 'chip activo' : 'chip'} onClick={() => filtro(fd, setFd, d.id)}>{d.nombre}</button>)}
          {TIPOS.filter(t => conteo[t.id] !== 0).map(t => <button key={t.id} className={ft.includes(t.id) ? 'chip activo' : 'chip'} onClick={() => filtro(ft, setFt, t.id)}>{t.nombre}</button>)}
        </div>
        <p className="ayuda">{total} productos · los más populares primero</p>
      </div>
      {parecidos && (
        <aside className="parecidos">
          <div className="titulo-fila"><b>Parecidos a «{parecidos.de.categoria_es}» que marcaste</b><button onClick={() => setParecidos(null)}>Cerrar ✕</button></div>
          <div className="carrusel">{parecidos.productos.map(p => <Tarjeta key={p.id} p={p} marcado={ids.has(p.id)}><Boton p={p} /></Tarjeta>)}</div>
        </aside>
      )}
      <div className="rejilla">{items.map(p => <Tarjeta key={p.id} p={p} marcado={ids.has(p.id)}><Boton p={p} /></Tarjeta>)}</div>
      {items.length < total && <p className="centro"><button onClick={() => setPagina(pagina + 1)}>Ver más productos</button></p>}
      <Barra>
        <button onClick={atras}>← Atrás</button>
        <span><b>{sel.length} de {MAX}</b> marcados</span>
        <button className="principal" disabled={cargando} onClick={ver}>{cargando ? 'Calculando…' : 'Ver mis recomendaciones →'}</button>
      </Barra>
    </section>
  )
}

function Evaluar({ estado, terminar, irAPerfil }: { estado: Estado; terminar: () => void; irAPerfil: () => void }) {
  const [ev, setEv] = useState<{ evaluacion_id: string; productos: Producto[] } | null>(null)
  const [juicios, setJuicios] = useState<Record<string, number | null>>({})
  const [enc, setEnc] = useState<Record<string, number | string | null>>({})
  const [error, setError] = useState('')
  const sinPerfil = !estado.disciplinas.length && !estado.selecciones.length

  if (!ev) return (
    <section className="estrecha">
      <h1>Valoración de sugerencias</h1>
      <p>Verás algunos productos en orden aleatorio. Valora qué tan pertinente te parece cada uno según tus intereses. Después responderás las preguntas de usabilidad y de experiencia.</p>
      {sinPerfil && <p className="aviso">Primero cuéntanos tus intereses: <button onClick={irAPerfil}>Ir a elegir deportes y productos</button></p>}
      {error && <p className="error">{error}</p>}
      <button className="principal" disabled={sinPerfil} onClick={async () => {
        try { setEv(await api('/evaluacion', 'POST')) } catch (e) { setError((e as Error).message) }
      }}>Empezar →</button>
    </section>
  )

  const faltan = ev.productos.filter(p => !(p.id in juicios)).length
  const faltanEnc = PREGUNTAS.filter(([k]) => !(k in enc)).length + SUS.filter((_, i) => !(`sus${i + 1}` in enc)).length
  return (
    <section>
      <h1>¿Qué tan pertinente es cada producto para ti?</h1>
      <p className="ayuda">1 = nada pertinente, 5 = muy pertinente. Si no puedes juzgarlo, elige «No puedo valorar». El orden es aleatorio.</p>
      <div className="rejilla">
        {ev.productos.map(p => (
          <Tarjeta key={p.id} p={p}>
            <div className="escala" role="radiogroup" aria-label={`Pertinencia de ${p.nombre}`}>
              {[1, 2, 3, 4, 5].map(v => <button key={v} className={juicios[p.id] === v ? 'activo' : ''} aria-pressed={juicios[p.id] === v} onClick={() => setJuicios({ ...juicios, [p.id]: v })}>{v}</button>)}
            </div>
            <button className={'no-puedo' + (p.id in juicios && juicios[p.id] === null ? ' activo' : '')} onClick={() => setJuicios({ ...juicios, [p.id]: null })}>No puedo valorar</button>
          </Tarjeta>
        ))}
      </div>
      <h2>Usabilidad de la herramienta</h2>
      <p className="ayuda">Por favor seleccione de cada uno de los enunciados la opción que mejor describa su experiencia con la herramienta electrónica. Un puntaje de 1 significa que usted se encuentra totalmente en desacuerdo con el enunciado, mientras que un puntaje en 5 significa que está totalmente de acuerdo, un puntaje de 3 significaría que usted se encuentra neutral con el enunciado.</p>
      <div className="encuesta">
        {SUS.map((t, i) => {
          const k = `sus${i + 1}`
          return (
            <fieldset key={k}><legend>{i + 1}. {t}</legend>
              {[1, 2, 3, 4, 5].map(v => <button key={v} className={enc[k] === v ? 'activo' : ''} aria-pressed={enc[k] === v} onClick={() => setEnc({ ...enc, [k]: v })}>{v}</button>)}
            </fieldset>
          )
        })}
      </div>
      <h2>Tu experiencia con Gearly</h2>
      <p className="ayuda">1 = totalmente en desacuerdo, 5 = totalmente de acuerdo.</p>
      <div className="encuesta">
        {PREGUNTAS.map(([k, t]) => (
          <fieldset key={k}><legend>{t}</legend>
            {[1, 2, 3, 4, 5].map(v => <button key={v} className={enc[k] === v ? 'activo' : ''} onClick={() => setEnc({ ...enc, [k]: v })}>{v}</button>)}
            <button className={k in enc && enc[k] === null ? 'activo' : ''} onClick={() => setEnc({ ...enc, [k]: null })}>No puedo evaluar</button>
          </fieldset>
        ))}
        <label>¿Qué interés o producto no pudiste expresar o encontrar? <textarea maxLength={500} onChange={e => setEnc({ ...enc, no_encontro: e.target.value })} /></label>
        <label>¿En qué momento tuviste dificultad? <textarea maxLength={500} onChange={e => setEnc({ ...enc, dificultad: e.target.value })} /></label>
        <label>¿Qué cambiarías primero de Gearly? <textarea maxLength={500} onChange={e => setEnc({ ...enc, cambiaria: e.target.value })} /></label>
      </div>
      {error && <p className="error">{error}</p>}
      <Barra>
        <span>{faltan ? `Faltan ${faltan} productos` : '✓ Productos valorados'} · {faltanEnc ? `faltan ${faltanEnc} preguntas` : '✓ preguntas'}</span>
        <button className="principal" disabled={faltan > 0 || faltanEnc > 0} onClick={async () => {
          try { await api(`/evaluacion/${ev.evaluacion_id}`, 'PUT', { juicios, encuesta: enc }); terminar() } catch (e) { setError((e as Error).message) }
        }}>Enviar respuestas</button>
      </Barra>
    </section>
  )
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
