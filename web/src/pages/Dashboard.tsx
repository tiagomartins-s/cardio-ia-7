import { useEffect, useState } from 'react'
import { api, API_URL, type Health, type LeituraIot, type Paciente, type PredicaoHistorico } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import Sparkline from '../components/Sparkline'

const POLL_MS = 5000

export default function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null)
  const [pacientes, setPacientes] = useState<Paciente[]>([])
  const [predicoes, setPredicoes] = useState<PredicaoHistorico[]>([])
  const [leituras, setLeituras] = useState<LeituraIot[]>([])
  const [erro, setErro] = useState('')

  async function carregar() {
    try {
      const [h, p, pr, l] = await Promise.all([
        api.health(),
        api.pacientes(),
        api.predicoes(8),
        api.leiturasIot(30),
      ])
      setHealth(h)
      setPacientes(p)
      setPredicoes(pr)
      setLeituras(l)
      setErro('')
    } catch (e) {
      setErro(`Não foi possível falar com a API (${API_URL}). ${String(e)}`)
    }
  }

  useEffect(() => {
    carregar()
    const t = setInterval(carregar, POLL_MS)
    return () => clearInterval(t)
  }, [])

  const ultima = leituras[0]
  const alertas = leituras.filter((l) => l.alerta).length
  const bpmSerie = [...leituras].reverse().map((l) => l.bpm ?? 0).filter((v) => v > 0)

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Dashboard clínico</h1>
          <div className="sub">
            Visão em tempo quase-real do ecossistema CardioIA (atualiza a cada {POLL_MS / 1000}s)
          </div>
        </div>
        {health && (
          <span className={`badge ${health.status === 'ok' ? 'ok' : 'ALTO'}`}>
            API {health.status.toUpperCase()} · {health.ambiente} · {health.banco.driver}
          </span>
        )}
      </div>

      {erro && <div className="card mb"><p className="error">{erro}</p></div>}

      <div className="grid cols-4 mb">
        <div className="card">
          <div className="label">Último BPM (IoT)</div>
          <div className="value">{ultima?.bpm ?? '—'} <span className="hint">bpm</span></div>
          <div className="hint">{ultima ? `dispositivo ${ultima.device_id}` : 'sem leituras ainda'}</div>
        </div>
        <div className="card">
          <div className="label">Temp. paciente</div>
          <div className="value">{ultima?.temperatura_pac ?? '—'} <span className="hint">°C</span></div>
          <div className="hint">ambiente: {ultima?.temperatura_amb ?? '—'}°C · {ultima?.umidade ?? '—'}%</div>
        </div>
        <div className="card">
          <div className="label">Alertas (últimas leituras)</div>
          <div className="value" style={{ color: alertas ? 'var(--bad)' : 'var(--ok)' }}>{alertas}</div>
          <div className="hint">de {leituras.length} leituras recebidas</div>
        </div>
        <div className="card">
          <div className="label">Pacientes</div>
          <div className="value">{pacientes.length}</div>
          <div className="hint">modelo: {health?.modelo.carregado ? `RF ${health.modelo.n_arvores} árvores` : 'heurística'}</div>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>📡 Frequência cardíaca — fluxo do sensor</h2>
          <Sparkline data={bpmSerie} />
          {ultima?.avaliacao?.motivos?.length ? (
            <p className="error">⚠ {ultima.avaliacao.motivos.join(' · ')}</p>
          ) : (
            <p className="muted">Sinais dentro das faixas de referência.</p>
          )}
        </div>

        <div className="card">
          <h2>🤖 Últimas predições do pipeline multiagente</h2>
          {predicoes.length === 0 && <p className="muted">Nenhuma predição ainda — use a aba Predição IA.</p>}
          <table>
            <tbody>
              {predicoes.map((p) => (
                <tr key={p.id}>
                  <td className="muted">#{p.id}</td>
                  <td>{p.payload.nome ?? 'anônimo'}</td>
                  <td>{(p.probabilidade * 100).toFixed(0)}%</td>
                  <td><RiskBadge value={p.classificacao} /></td>
                  <td><span className={`badge ${p.payload.nivel_atencao}`}>{p.payload.nivel_atencao}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
