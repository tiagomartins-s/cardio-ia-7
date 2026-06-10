import { useEffect, useRef, useState } from 'react'
import { api, type Predicao } from '../lib/api'
import RiskBadge from '../components/RiskBadge'

interface Msg {
  autor: 'user' | 'bot'
  texto: string
  triagem?: Predicao | null
}

const SUGESTOES_INICIAIS = [
  'Estou com dor no peito',
  'Quero agendar um eletrocardiograma',
  'Minha pressão está 15 por 9',
  'Quais os sintomas de um infarto?',
]

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([
    {
      autor: 'bot',
      texto:
        'Olá! Sou a assistente virtual da CardioIA 🫀\nPosso avaliar sintomas, agendar exames ou tirar dúvidas sobre pressão arterial. Como posso ajudar?',
    },
  ])
  const [sugestoes, setSugestoes] = useState<string[]>(SUGESTOES_INICIAIS)
  const [texto, setTexto] = useState('')
  const [sessao, setSessao] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(false)
  const fim = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs])

  async function enviar(t?: string) {
    const msg = (t ?? texto).trim()
    if (!msg || carregando) return
    setTexto('')
    setMsgs((m) => [...m, { autor: 'user', texto: msg }])
    setCarregando(true)
    try {
      const r = await api.chat(msg, sessao)
      setSessao(r.sessao_id)
      setMsgs((m) => [...m, { autor: 'bot', texto: r.resposta, triagem: r.triagem }])
      setSugestoes(r.sugestoes)
    } catch (e) {
      setMsgs((m) => [...m, { autor: 'bot', texto: `Erro ao falar com a API: ${String(e)}` }])
    } finally {
      setCarregando(false)
    }
  }

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Chat do paciente</h1>
          <div className="sub">
            Intents da Fase 5 (ex-Watson) + triagem guiada com o pipeline multiagente da Fase 6
          </div>
        </div>
        {sessao && <span className="muted" style={{ fontSize: '0.75rem' }}>sessão {sessao}</span>}
      </div>

      <div className="card chat-box">
        <div className="chat-msgs">
          {msgs.map((m, i) => (
            <div key={i} className={`msg ${m.autor}`}>
              {m.texto}
              {m.triagem && (
                <div className="mt" style={{ fontSize: '0.8rem' }}>
                  <RiskBadge value={m.triagem.classificacao} />{' '}
                  <span className={`badge ${m.triagem.nivel_atencao}`}>{m.triagem.nivel_atencao}</span>
                  <div className="muted">
                    {m.triagem.protocolos.map((p) => p.codigo).join(' · ')}
                  </div>
                </div>
              )}
            </div>
          ))}
          {carregando && <div className="msg bot pulse">digitando…</div>}
          <div ref={fim} />
        </div>

        {sugestoes.length > 0 && (
          <div className="chips">
            {sugestoes.map((s) => (
              <span key={s} className="chip" onClick={() => enviar(s)}>{s}</span>
            ))}
          </div>
        )}

        <form
          className="chat-input"
          onSubmit={(e) => {
            e.preventDefault()
            enviar()
          }}
        >
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Escreva sua mensagem…"
            autoFocus
          />
          <button type="submit" disabled={carregando}>Enviar</button>
        </form>
      </div>
    </>
  )
}
