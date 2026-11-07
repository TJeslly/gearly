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
const PREGUNTAS = [
  ['intereses', 'Entendí para qué se pedían mis intereses.'],
  ['expresar', 'Pude expresar mis intereses con las opciones disponibles.'],
  ['comprar', 'Entendí que marcar un producto no significa comprarlo.'],
  ['explicacion', 'Comprendí por qué me recomendaron al menos un producto.'],
  ['cambiar', 'Encontré cómo cambiar mis preferencias.'],
  ['pasos', 'La cantidad de pasos me pareció razonable.'],
]

type Paso = 'inicio' | 'deportes' | 'tipos' | 'gustos' | 'recomendaciones' | 'evaluar' | 'gracias'

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
    setLista(await api<Lista>('/recomendaciones?metodo=hibrido'))
    setPaso('recomendaciones'); window.scrollTo(0, 0)
  })
  const reiniciar = () => accion(async () => {
    const e = await api<Estado>('/perfil', 'DELETE'); setEstado(e); setDisc([]); setTipos([]); setSel([]); setLista(null); setPaso('deportes')
  })
  const alternar = <T,>(xs: T[], x: T) => xs.includes(x) ? xs.filter(y => y !== x) : [...xs, x]

  if (!estado) return <main className="centro">{error ? <p className="error">{error}</p> : <p>Cargando Gearly… (la primera vez puede tardar un minuto)</p>}</main>

  return (
    <>
      <header className="cabecera">
        <button className="logo" onClick={() => setPaso('inicio')}>Gearly</button>
        <Pasos paso={paso} ir={setPaso} />
        <span className="codigo" title="Con este código puedes retomar tu perfil durante 7 días">Tu código: <b>{estado.codigo}</b></span>
      </header>
      {error && <p className="error" role="alert">{error}</p>}
      <main>
        {paso === 'inicio' && <Inicio continuar={() => setPaso('deportes')} evaluar={() => setPaso('evaluar')} retomado={e => { setEstado(e); setDisc(e.disciplinas); setTipos(e.tipos); setSel(e.selecciones) }} />}

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
                <button className="principal" onClick={() => setPaso('evaluar')}>Evaluar estas sugerencias</button>
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
        {paso === 'gracias' && <section className="centro"><h1>¡Gracias por participar!</h1><p>Tus respuestas quedaron guardadas con tu código. Ya puedes cerrar esta página.</p></section>}
      </main>
      <footer>Prototipo académico · Universidad Manuela Beltrán · Datos de productos: Amazon Reviews 2023 (McAuley Lab). No es una tienda.</footer>
    </>
  )
}

function Barra({ children }: { children: React.ReactNode }) {
  return <div className="barra">{children}</div>
}

function Inicio({ continuar, evaluar, retomado }: { continuar: () => void; evaluar: () => void; retomado: (e: Estado) => void }) {
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
        <button onClick={evaluar}>Participar en la evaluación</button>
      </div>
      <details>
        <summary>¿Ya tienes un código?</summary>
        <form className="fila" onSubmit={async e => {
          e.preventDefault(); setMsg('')
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
  const [acepta, setAcepta] = useState(false)
  const [codigo, setCodigo] = useState('')
  const [ev, setEv] = useState<{ evaluacion_id: string; productos: Producto[] } | null>(null)
  const [juicios, setJuicios] = useState<Record<string, number | null>>({})
  const [enc, setEnc] = useState<Record<string, number | string | null>>({})
  const [error, setError] = useState('')
  const sinPerfil = !estado.disciplinas.length && !estado.selecciones.length

  if (!ev) return (
    <section className="estrecha">
      <h1>Evaluación de Gearly</h1>
      <p>Vas a valorar qué tan pertinentes te parecen algunos productos según tus intereses y luego responder seis preguntas cortas. Toma unos 10 minutos.</p>
      <ul className="nota">
        <li>Participar es voluntario y puedes dejarlo cuando quieras.</li>
        <li>Debes ser mayor de edad. No pedimos nombre ni correo; tus respuestas se guardan con el código que te dio el equipo.</li>
        <li>Los datos se usan solo para el trabajo de grado (Ley 1581 de 2012).</li>
      </ul>
      {sinPerfil && <p className="aviso">Primero cuéntanos tus intereses: <button onClick={irAPerfil}>Ir a elegir deportes y productos</button></p>}
      <label className="check"><input type="checkbox" checked={acepta} onChange={e => setAcepta(e.target.checked)} /> Leí la información y acepto participar.</label>
      <label>Código de participante <input value={codigo} onChange={e => setCodigo(e.target.value)} placeholder="P001" /></label>
      {error && <p className="error">{error}</p>}
      <button className="principal" disabled={!acepta || codigo.trim().length < 2 || sinPerfil} onClick={async () => {
        try { setEv(await api('/evaluacion', 'POST', { codigo_participante: codigo })) } catch (e) { setError((e as Error).message) }
      }}>Empezar evaluación →</button>
    </section>
  )

  const faltan = ev.productos.filter(p => !(p.id in juicios)).length
  const faltanEnc = PREGUNTAS.filter(([k]) => !(k in enc)).length
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
      <h2>Tu experiencia</h2>
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
