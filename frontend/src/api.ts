export type Producto = {
  id: string; nombre: string; marca: string; disciplina: string; tipo: string
  categoria_es: string; imagen: string; ruta: string[]
}
export type Participacion = { codigo: string; estado: 'activa' | 'excluida' | 'retirada'; terminada?: boolean } | null
export type Estado = { codigo: string; participacion: Participacion; version: number; disciplinas: string[]; tipos: string[]; selecciones: Producto[] }
export type Resultado = { producto: Producto; puntaje: number; explicacion: string }
export type Lista = { lista_id: string; metodo: string; motivo_alternativa: string | null; resultados: Resultado[] }

let csrf = ''

export class ErrorApi extends Error {
  constructor(public status: number, mensaje: string) { super(mensaje) }
}

export async function api<T>(ruta: string, metodo = 'GET', cuerpo?: unknown): Promise<T> {
  const r = await fetch('/api' + ruta, {
    method: metodo,
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(metodo !== 'GET' && csrf ? { 'X-CSRF': csrf } : {}) },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  })
  const datos = await r.json().catch(() => ({}))
  if (!r.ok) throw new ErrorApi(r.status, (datos as { detail?: string }).detail ?? 'Ocurrió un error. Intenta de nuevo.')
  if ((datos as { csrf?: string }).csrf) csrf = (datos as { csrf: string }).csrf
  return datos as T
}

/** Recupera la sesión guardada en la cookie o crea una nueva. */
export async function iniciarSesion(): Promise<Estado> {
  try { return await api<Estado>('/sesiones/actual') }
  catch (e) { if (e instanceof ErrorApi && e.status === 401) return api<Estado>('/sesiones', 'POST'); throw e }
}
