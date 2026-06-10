import { useEffect, useState } from 'react'
import { api, type Paciente } from '../lib/api'

type FormPaciente = { nome: string; idade: number; sexo: 'F' | 'M' | 'O'; observacoes: string }
const NOVO: FormPaciente = { nome: '', idade: 50, sexo: 'O', observacoes: '' }

export default function Pacientes() {
  const [pacientes, setPacientes] = useState<Paciente[]>([])
  const [form, setForm] = useState({ ...NOVO })
  const [erro, setErro] = useState('')

  async function carregar() {
    try {
      setPacientes(await api.pacientes())
    } catch (e) {
      setErro(String(e))
    }
  }

  useEffect(() => {
    carregar()
  }, [])

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    setErro('')
    try {
      await api.criarPaciente(form)
      setForm({ ...NOVO })
      carregar()
    } catch (er) {
      setErro(String(er))
    }
  }

  async function remover(id: number) {
    if (!confirm('Remover este paciente?')) return
    await api.removerPaciente(id)
    carregar()
  }

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Pacientes</h1>
          <div className="sub">Cadastro usado pelo pipeline de predição e pelo monitor IoT</div>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Novo paciente</h2>
          <form onSubmit={salvar}>
            <label className="field">
              <span>Nome completo</span>
              <input
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                required
                minLength={2}
              />
            </label>
            <div className="grid cols-2">
              <label className="field">
                <span>Idade</span>
                <input
                  type="number"
                  min={0}
                  max={120}
                  value={form.idade}
                  onChange={(e) => setForm((f) => ({ ...f, idade: Number(e.target.value) }))}
                />
              </label>
              <label className="field">
                <span>Sexo</span>
                <select
                  value={form.sexo}
                  onChange={(e) => setForm((f) => ({ ...f, sexo: e.target.value as Paciente['sexo'] }))}
                >
                  <option value="F">Feminino</option>
                  <option value="M">Masculino</option>
                  <option value="O">Outro / não informar</option>
                </select>
              </label>
            </div>
            <label className="field">
              <span>Observações clínicas</span>
              <textarea
                rows={3}
                value={form.observacoes}
                onChange={(e) => setForm((f) => ({ ...f, observacoes: e.target.value }))}
              />
            </label>
            {erro && <p className="error mb">{erro}</p>}
            <button type="submit">＋ Cadastrar</button>
          </form>
        </div>

        <div className="card">
          <h2>Cadastrados ({pacientes.length})</h2>
          <table>
            <thead>
              <tr><th>Nome</th><th>Idade</th><th>Sexo</th><th>Obs.</th><th /></tr>
            </thead>
            <tbody>
              {pacientes.map((p) => (
                <tr key={p.id}>
                  <td><b>{p.nome}</b></td>
                  <td>{p.idade}</td>
                  <td>{p.sexo}</td>
                  <td className="muted" style={{ maxWidth: 220 }}>{p.observacoes}</td>
                  <td>
                    <button className="ghost small" onClick={() => remover(p.id)}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
