import { useState } from 'react'
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { logout, usuarioAtual, type Usuario } from './auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Pacientes from './pages/Pacientes'
import Predicao from './pages/Predicao'
import TriagemNlp from './pages/TriagemNlp'
import Protocolos from './pages/Protocolos'
import Modelo from './pages/Modelo'
import Chat from './pages/Chat'
import Iot from './pages/Iot'

const NAV = [
  { to: '/', icon: '📊', label: 'Dashboard' },
  { to: '/iot', icon: '📡', label: 'Monitor IoT' },
  { to: '/predicao', icon: '🤖', label: 'Predição IA' },
  { to: '/triagem', icon: '📝', label: 'Triagem NLP' },
  { to: '/chat', icon: '💬', label: 'Chat Paciente' },
  { to: '/pacientes', icon: '🧑‍⚕️', label: 'Pacientes' },
  { to: '/protocolos', icon: '📋', label: 'Protocolos' },
  { to: '/modelo', icon: '📈', label: 'Modelo ML' },
]

export default function App() {
  const [user, setUser] = useState<Usuario | null>(usuarioAtual())
  const navigate = useNavigate()

  if (!user) {
    return <Login onLogin={(u) => setUser(u)} />
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">🫀</span>
          <div>
            <b>CardioIA</b>
            <small>Fase 7 — Plataforma Total</small>
          </div>
        </div>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === '/'}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <span>{n.icon}</span> {n.label}
          </NavLink>
        ))}
        <div className="spacer" />
        <div className="nav-item">
          <span>👤</span> {user.nome} <span className="muted">({user.perfil})</span>
        </div>
        <div
          className="nav-item"
          onClick={() => {
            logout()
            setUser(null)
            navigate('/')
          }}
        >
          <span>🚪</span> Sair
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/iot" element={<Iot />} />
          <Route path="/predicao" element={<Predicao />} />
          <Route path="/triagem" element={<TriagemNlp />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/pacientes" element={<Pacientes />} />
          <Route path="/protocolos" element={<Protocolos />} />
          <Route path="/modelo" element={<Modelo />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
