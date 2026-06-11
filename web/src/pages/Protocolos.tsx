import { useEffect, useState } from 'react'
import { api, type GatilhoProtocolo, type Protocolo } from '../lib/api'
import RiskBadge from '../components/RiskBadge'

function formatGatilho(g: GatilhoProtocolo): string {
  const valor =
    typeof g.valor === 'boolean' ? (g.valor ? 'sim' : 'não') : String(g.valor)
  return `${g.campo.replace(/_/g, ' ')} ${g.op} ${valor}`
}

export default function Protocolos() {
  const [protocolos, setProtocolos] = useState<Protocolo[]>([])
  const [erro, setErro] = useState('')

  useEffect(() => {
    api.protocolos().then(setProtocolos).catch((e) => setErro(String(e)))
  }, [])

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Base de protocolos clínicos</h1>
          <div className="sub">Consultada pelo Agente Especialista em Protocolos durante as predições</div>
        </div>
      </div>

      {erro && <div className="card mb"><p className="error">{erro}</p></div>}

      <div className="grid cols-2">
        {protocolos.map((p) => (
          <div className="card" key={p.id}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h2>{p.codigo} — {p.titulo}</h2>
              <RiskBadge value={p.severidade} />
            </div>
            <p className="muted">{p.descricao}</p>
            <div className="chips">
              {p.gatilhos.map((g, i) => (
                <span key={`${g.campo}-${g.op}-${i}`} className="chip">{formatGatilho(g)}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
