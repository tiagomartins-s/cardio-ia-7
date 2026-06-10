import { useEffect, useState } from 'react'
import { api, type LeituraIot } from '../lib/api'
import Sparkline from '../components/Sparkline'

export default function Iot() {
  const [leituras, setLeituras] = useState<LeituraIot[]>([])
  const [erro, setErro] = useState('')

  async function carregar() {
    try {
      setLeituras(await api.leiturasIot(50))
      setErro('')
    } catch (e) {
      setErro(String(e))
    }
  }

  useEffect(() => {
    carregar()
    const t = setInterval(carregar, 4000)
    return () => clearInterval(t)
  }, [])

  const serie = [...leituras].reverse()

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Monitor IoT — ESP32 / MicroPython</h1>
          <div className="sub">
            Leituras enviadas pelo dispositivo simulado no Wokwi via HTTP (Fase 3 → MicroPython)
          </div>
        </div>
        <span className="badge ok pulse">● ao vivo</span>
      </div>

      {erro && <div className="card mb"><p className="error">{erro}</p></div>}

      <div className="grid cols-2 mb">
        <div className="card">
          <h2>BPM</h2>
          <Sparkline data={serie.map((l) => l.bpm ?? 0).filter((v) => v > 0)} color="var(--primary)" />
        </div>
        <div className="card">
          <h2>Temperatura do paciente (°C)</h2>
          <Sparkline
            data={serie.map((l) => l.temperatura_pac ?? 0).filter((v) => v > 0)}
            color="var(--warn)"
          />
        </div>
      </div>

      <div className="card">
        <h2>Leituras recebidas</h2>
        {leituras.length === 0 && (
          <p className="muted">
            Nenhuma leitura ainda. Rode a simulação no Wokwi (pasta <code>iot/</code>) apontando para esta API.
          </p>
        )}
        <table>
          <thead>
            <tr>
              <th>#</th><th>Dispositivo</th><th>BPM</th><th>T. amb</th><th>Umid.</th>
              <th>T. pac</th><th>Edge</th><th>Servidor</th><th>Motivos</th><th>Quando (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {leituras.map((l) => (
              <tr key={l.id}>
                <td className="muted">{l.id}</td>
                <td>{l.device_id}</td>
                <td><b>{l.bpm ?? '—'}</b></td>
                <td>{l.temperatura_amb ?? '—'}</td>
                <td>{l.umidade ?? '—'}</td>
                <td>{l.temperatura_pac ?? '—'}</td>
                <td>{l.status_edge && <span className={`badge ${l.status_edge}`}>{l.status_edge}</span>}</td>
                <td>{l.avaliacao && <span className={`badge ${l.avaliacao.status_servidor}`}>{l.avaliacao.status_servidor}</span>}</td>
                <td className="muted" style={{ maxWidth: 260 }}>{l.avaliacao?.motivos.join('; ') || '—'}</td>
                <td className="muted">{new Date(l.criado_em).toLocaleTimeString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
