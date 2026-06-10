import { useState } from 'react'
import { api, type TriagemNlp as Resultado } from '../lib/api'

const EXEMPLOS = [
  'sinto dor no peito e falta de ar',
  'tenho sentido cansaço constante e inchaço nos tornozelos',
  'meu coração está batendo forte e sinto tontura',
  'sinto uma dor em queimação após as refeições',
]

export default function TriagemNlp() {
  const [texto, setTexto] = useState('')
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')

  async function analisar(t?: string) {
    const alvo = (t ?? texto).trim()
    if (alvo.length < 3) return
    if (t) setTexto(t)
    setCarregando(true)
    setErro('')
    try {
      setResultado(await api.triagemNlp(alvo))
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
          <h1>Triagem por texto livre (NLP — Fase 2)</h1>
          <div className="sub">Ontologia médica + classificador TF-IDF/Regressão Logística (93% acurácia)</div>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Relato do paciente</h2>
          <textarea
            rows={4}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Descreva os sintomas com suas palavras…"
          />
          <div className="chips mb">
            {EXEMPLOS.map((ex) => (
              <span key={ex} className="chip" onClick={() => analisar(ex)}>{ex}</span>
            ))}
          </div>
          {erro && <p className="error mb">{erro}</p>}
          <button onClick={() => analisar()} disabled={carregando}>
            {carregando ? 'Analisando…' : '🔎 Analisar relato'}
          </button>
        </div>

        <div className="card">
          <h2>Análise</h2>
          {!resultado && <p className="muted">O resultado da triagem aparecerá aqui.</p>}
          {resultado && (
            <>
              <div className="row mb">
                <div className="card" style={{ flex: 1, textAlign: 'center' }}>
                  <div className="label">Risco textual</div>
                  <div className="value">
                    <span className={`badge ${resultado.risco_textual === 'alto risco' ? 'ALTO' : 'BAIXO'}`}>
                      {resultado.risco_textual.toUpperCase()}
                    </span>
                  </div>
                </div>
                <div className="card" style={{ flex: 1, textAlign: 'center' }}>
                  <div className="label">Probabilidade</div>
                  <div className="value">{(resultado.probabilidade_risco * 100).toFixed(0)}%</div>
                </div>
              </div>

              <h2>Sintomas detectados (ontologia)</h2>
              {resultado.sintomas_detectados.length === 0 && <p className="muted">Nenhum termo da ontologia encontrado.</p>}
              <div className="chips mb">
                {resultado.sintomas_detectados.map((s) => (
                  <span key={s} className="chip" style={{ color: 'var(--warn)' }}>{s}</span>
                ))}
              </div>

              <h2>Diagnósticos sugeridos</h2>
              {resultado.diagnosticos.length === 0 && <p className="muted">Sem sugestão — encaminhar para avaliação humana.</p>}
              <table>
                <tbody>
                  {resultado.diagnosticos.map((d) => (
                    <tr key={d.diagnostico}>
                      <td>{d.diagnostico}</td>
                      <td className="muted">evidência: {d.forca_evidencia}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="muted mt" style={{ fontSize: '0.75rem' }}>
                motor: {resultado.fonte} · uso educacional, não substitui avaliação médica
              </p>
            </>
          )}
        </div>
      </div>
    </>
  )
}
