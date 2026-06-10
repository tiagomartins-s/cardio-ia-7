// Cliente da CardioIA API para o app mobile.
// A URL vem de EXPO_PUBLIC_API_URL (definida no eas.json para builds EAS,
// ou em .env para desenvolvimento com `expo start`).

export const API_URL: string =
  process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'http://10.0.2.2:8765'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!r.ok) throw new Error(`API ${r.status}`)
  return r.json()
}

export interface LeituraIot {
  id: number
  device_id: string
  bpm: number | null
  temperatura_amb: number | null
  umidade: number | null
  temperatura_pac: number | null
  status_edge: string | null
  alerta: boolean
  avaliacao: { motivos: string[]; status_servidor: string } | null
  criado_em: string
}

export interface PredicaoHistorico {
  id: number
  probabilidade: number
  classificacao: string
  payload: { nome: string | null; nivel_atencao: string; recomendacao_final: string }
  criado_em: string
}

export interface ChatTurno {
  sessao_id: string
  resposta: string
  estado: string
  sugestoes: string[]
}

export interface Health {
  status: string
  modelo: { carregado: boolean; n_arvores: number }
}

export const api = {
  health: () => req<Health>('/api/health'),
  leiturasIot: (limite = 30) => req<LeituraIot[]>(`/api/iot/leituras?limite=${limite}`),
  predicoes: (limite = 10) => req<PredicaoHistorico[]>(`/api/predicoes?limite=${limite}`),
  chat: (mensagem: string, sessao_id?: string | null) =>
    req<ChatTurno>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ mensagem, sessao_id: sessao_id ?? undefined }),
    }),
}
