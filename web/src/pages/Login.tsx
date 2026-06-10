import { useState } from 'react'
import { login, type Usuario } from '../auth'

export default function Login({ onLogin }: { onLogin: (u: Usuario) => void }) {
  const [nome, setNome] = useState('')
  const [perfil, setPerfil] = useState<Usuario['perfil']>('medico')
  const [erro, setErro] = useState('')

  function entrar(e: React.FormEvent) {
    e.preventDefault()
    if (nome.trim().length < 2) {
      setErro('Informe seu nome para entrar.')
      return
    }
    onLogin(login(nome.trim(), perfil))
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="card">
          <div className="brand mb" style={{ justifyContent: 'center' }}>
            <span className="logo" style={{ fontSize: '2.2rem' }}>🫀</span>
            <div>
              <b style={{ fontSize: '1.3rem' }}>CardioIA</b>
              <small>Plataforma de Inteligência Cardíaca Total</small>
            </div>
          </div>
          <form onSubmit={entrar}>
            <label className="field">
              <span>Nome</span>
              <input
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Como devemos te chamar?"
                autoFocus
              />
            </label>
            <label className="field">
              <span>Perfil de acesso</span>
              <select value={perfil} onChange={(e) => setPerfil(e.target.value as Usuario['perfil'])}>
                <option value="medico">Equipe médica</option>
                <option value="paciente">Paciente</option>
              </select>
            </label>
            {erro && <p className="error mb">{erro}</p>}
            <button type="submit" style={{ width: '100%' }}>Entrar na plataforma</button>
          </form>
          <p className="muted mt" style={{ fontSize: '0.75rem', textAlign: 'center' }}>
            MVP acadêmico (FIAP — Fase 7). Não substitui atendimento médico.
          </p>
        </div>
      </div>
    </div>
  )
}
