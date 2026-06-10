import { useEffect, useState } from 'react'
import { api, type Paciente, type Predicao, type SinaisVitais } from '../lib/api'
import RiskBadge from '../components/RiskBadge'

const SINAIS_INICIAIS: SinaisVitais = {
  idade: 60,
  frequencia_cardiaca: 80,
  spo2: 97,
  pressao_sistolica: 130,
  pressao_diastolica: 85,
  glicemia: 110,
  dor_toracica: false,
  historico_arritmia: false,
  historico_infarto: false,
  tabagista: false,
  diabetico: false,
  carga_sistema: 0.5,
  recursos_disponiveis: 0.7,
}

const CAMPOS_NUM: { k: keyof SinaisVitais; label: string }[] = [
  { k: 'idade', label: 'Idade' },
  { k: 'frequencia_cardiaca', label: 'Freq. cardíaca (bpm)' },
  { k: 'spo2', label: 'SpO2 (%)' },
  { k: 'pressao_sistolica', label: 'Pressão sistólica' },
  { k: 'pressao_diastolica', label: 'Pressão diastólica' },
  { k: 'glicemia', label: 'Glicemia (mg/dL)' },
]

const CAMPOS_BOOL: { k: keyof SinaisVitais; label: string }[] = [
  { k: 'dor_toracica', label: 'Dor torácica' },
  { k: 'historico_arritmia', label: 'Histórico de arritmia' },
  { k: 'historico_infarto', label: 'Histórico de infarto' },
  { k: 'tabagista', label: 'Tabagista' },
  { k: 'diabetico', label: 'Diabético' },
]

export default function PredicaoPage() {
  const [pacientes, setPacientes] = useState<Paciente[]>([])
  const [pacienteId, setPacienteId] = useState<string>('')
  const [sinais, setSinais] = useState<SinaisVitais>(SINAIS_INICIAIS)
  const [resultado, setResultado] = useState<Predicao | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [mostrarTrace, setMostrarTrace] = useState(false)
  const [erro, setErro] = useState('')

  useEffect(() => {
    api.pacientes().then(setPacientes).catch(() => {})
  }, [])

  function setNum(k: keyof SinaisVitais, v: string) {
    setSinais((s) => ({ ...s, [k]: Number(v) }))
  }

  async function executar() {
    setCarregando(true)
    setErro('')
    try {
      const r = await api.predizer({
        paciente_id: pacienteId ? Number(pacienteId) : null,
        sinais,
      })
      setResultado(r)
    } catch (e) {
      setErro(String(e))
    } finally {
      setCarregando(false)
    }
  }

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Predição de pico de risco — pipeline multiagente</h1>
          <div className="sub">Orquestrador → Analista de Risco (Random Forest) → Especialista em Protocolos</div>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Sinais vitais</h2>
          <label className="field">
            <span>Paciente (opcional)</span>
            <select value={pacienteId} onChange={(e) => setPacienteId(e.target.value)}>
              <option value="">— anônimo —</option>
              {pacientes.map((p) => (
                <option key={p.id} value={p.id}>{p.nome} ({p.idade} anos)</option>
              ))}
            </select>
          </label>
          <div className="grid cols-2">
            {CAMPOS_NUM.map((c) => (
              <label className="field" key={c.k}>
                <span>{c.label}</span>
                <input
                  type="number"
                  step="any"
                  value={String(sinais[c.k])}
                  onChange={(e) => setNum(c.k, e.target.value)}
                />
              </label>
            ))}
          </div>
          <div className="grid cols-2 mb">
            {CAMPOS_BOOL.map((c) => (
              <label className="check" key={c.k}>
                <input
                  type="checkbox"
                  checked={Boolean(sinais[c.k])}
                  onChange={(e) => setSinais((s) => ({ ...s, [c.k]: e.target.checked }))}
                />
                {c.label}
              </label>
            ))}
          </div>
          <div className="grid cols-2">
            <label className="field">
              <span>Carga do sistema ({sinais.carga_sistema})</span>
              <input type="range" min="0" max="1" step="0.05" value={sinais.carga_sistema}
                onChange={(e) => setNum('carga_sistema', e.target.value)} />
            </label>
            <label className="field">
              <span>Recursos disponíveis ({sinais.recursos_disponiveis})</span>
              <input type="range" min="0" max="1" step="0.05" value={sinais.recursos_disponiveis}
                onChange={(e) => setNum('recursos_disponiveis', e.target.value)} />
            </label>
          </div>
          {erro && <p className="error mb">{erro}</p>}
          <button onClick={executar} disabled={carregando}>
            {carregando ? 'Executando agentes…' : '▶ Executar pipeline de IA'}
          </button>
        </div>

        <div className="card">
          <h2>Resultado</h2>
          {!resultado && <p className="muted">Preencha os sinais e execute o pipeline.</p>}
          {resultado && (
            <>
              <div className="row mb">
                <div className="card" style={{ flex: 1, textAlign: 'center' }}>
                  <div className="label">Probabilidade</div>
                  <div className="value">{(resultado.probabilidade * 100).toFixed(1)}%</div>
                </div>
                <div className="card" style={{ flex: 1, textAlign: 'center' }}>
                  <div className="label">Classificação</div>
                  <div className="value"><RiskBadge value={resultado.classificacao} /></div>
                </div>
                <div className="card" style={{ flex: 1, textAlign: 'center' }}>
                  <div className="label">Atenção</div>
                  <div className="value"><span className={`badge ${resultado.nivel_atencao}`}>{resultado.nivel_atencao}</span></div>
                </div>
              </div>

              <p><b>Recomendação:</b> {resultado.recomendacao_final}</p>

              {resultado.fatores_relevantes.length > 0 && (
                <>
                  <h2 className="mt">Fatores relevantes</h2>
                  <ul>
                    {resultado.fatores_relevantes.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </>
              )}

              {resultado.protocolos.length > 0 && (
                <>
                  <h2>Protocolos acionados</h2>
                  <table className="mb">
                    <tbody>
                      {resultado.protocolos.map((p) => (
                        <tr key={p.codigo}>
                          <td><b>{p.codigo}</b></td>
                          <td>{p.titulo}</td>
                          <td><RiskBadge value={p.severidade} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              <button className="ghost small" onClick={() => setMostrarTrace((v) => !v)}>
                {mostrarTrace ? 'Ocultar' : 'Mostrar'} trace dos agentes ({resultado.trace.length} mensagens)
              </button>
              {mostrarTrace && (
                <div className="trace mt">
                  {resultado.trace.map((t, i) => (
                    <div className="trace-item" key={i}>
                      <span className="agent">{t.agente}</span>
                      <span className="role">{t.papel}</span>
                      <span>{t.conteudo}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  )
}
