// Cliente da CardioIA API (backend integrador — Fase 7)

export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://127.0.0.1:8765";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    throw new Error(`API ${r.status}: ${detail.slice(0, 200)}`);
  }
  if (r.status === 204) return undefined as T;
  return r.json();
}

// ---------- tipos ----------

export interface Paciente {
  id: number;
  nome: string;
  idade: number;
  sexo: "F" | "M" | "O";
  documento?: string | null;
  telefone?: string | null;
  observacoes?: string | null;
  criado_em: string;
}

export interface SinaisVitais {
  idade: number;
  frequencia_cardiaca: number;
  spo2: number;
  pressao_sistolica: number;
  pressao_diastolica: number;
  glicemia: number;
  dor_toracica: boolean;
  historico_arritmia: boolean;
  historico_infarto: boolean;
  tabagista: boolean;
  diabetico: boolean;
  carga_sistema: number;
  recursos_disponiveis: number;
}

export type Classificacao = "BAIXO" | "MODERADO" | "ALTO" | "CRITICO";
export type NivelAtencao = "rotina" | "monitorar" | "urgente" | "emergencia";

export interface ProtocoloItem {
  codigo: string;
  titulo: string;
  descricao: string;
  severidade: Classificacao;
}

export interface TraceMensagem {
  agente: string;
  papel: string;
  conteudo: string;
  metadados: Record<string, unknown>;
  timestamp: string;
}

export interface Predicao {
  paciente_id: number | null;
  nome: string | null;
  probabilidade: number;
  classificacao: Classificacao;
  nivel_atencao: NivelAtencao;
  fatores_relevantes: string[];
  protocolos: ProtocoloItem[];
  recomendacao_final: string;
  trace: TraceMensagem[];
  gerado_em: string;
}

export interface PredicaoHistorico {
  id: number;
  paciente_id: number | null;
  probabilidade: number;
  classificacao: Classificacao;
  payload: Predicao;
  criado_em: string;
}

export interface LeituraIot {
  id: number;
  device_id: string;
  bpm: number | null;
  temperatura_amb: number | null;
  umidade: number | null;
  temperatura_pac: number | null;
  status_edge: string | null;
  alerta: boolean;
  avaliacao: {
    alerta: boolean;
    motivos: string[];
    status_servidor: "NORMAL" | "ATENCAO" | "CRITICO";
    predicao?: Predicao | null;
  } | null;
  criado_em: string;
}

export interface ChatTurno {
  sessao_id: string;
  resposta: string;
  estado: string;
  intencao?: string | null;
  sugestoes: string[];
  triagem?: Predicao | null;
}

export interface TriagemNlp {
  texto: string;
  sintomas_detectados: string[];
  diagnosticos: { diagnostico: string; forca_evidencia: number }[];
  risco_textual: string;
  probabilidade_risco: number;
  fonte: string;
}

export interface ModelMetrics {
  accuracy: number;
  roc_auc: number;
  confusion_matrix: number[][];
  feature_importance: Record<string, number>;
}

export interface Health {
  status: string;
  ambiente: string;
  banco: { driver: string; persistente: boolean };
  modelo: { carregado: boolean; fallback: boolean; n_arvores: number };
  nlp: { regras_ontologia: number; classificador_carregado: boolean };
}

export interface Protocolo extends ProtocoloItem {
  id: number;
  gatilhos: string[];
}

// ---------- chamadas ----------

export const api = {
  health: () => req<Health>("/api/health"),
  metrics: () => req<ModelMetrics | null>("/api/modelo/metrics"),

  pacientes: () => req<Paciente[]>("/api/pacientes"),
  criarPaciente: (p: Omit<Paciente, "id" | "criado_em">) =>
    req<Paciente>("/api/pacientes", { method: "POST", body: JSON.stringify(p) }),
  removerPaciente: (id: number) =>
    req<void>(`/api/pacientes/${id}`, { method: "DELETE" }),

  protocolos: () => req<Protocolo[]>("/api/protocolos"),

  predizer: (body: { paciente_id?: number | null; nome?: string | null; sinais: SinaisVitais }) =>
    req<Predicao>("/api/predicoes", { method: "POST", body: JSON.stringify(body) }),
  predicoes: (limite = 20) => req<PredicaoHistorico[]>(`/api/predicoes?limite=${limite}`),

  triagemNlp: (texto: string) =>
    req<TriagemNlp>("/api/triagem-nlp", { method: "POST", body: JSON.stringify({ texto }) }),

  leiturasIot: (limite = 50) => req<LeituraIot[]>(`/api/iot/leituras?limite=${limite}`),

  chat: (mensagem: string, sessao_id?: string | null) =>
    req<ChatTurno>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ mensagem, sessao_id: sessao_id ?? undefined }),
    }),
};
