import { useEffect, useState } from 'react'
import { api, type Health, type ModelMetrics } from '../lib/api'

export default function Modelo() {
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    api.metrics().then(setMetrics).catch((e) => setErro(String(e)))
    api.health().then(setHealth).catch(() => {})
  }, [])

  const importancias = metrics
    ? Object.entries(metrics.feature_importance).sort((a, b) => b[1] - a[1])
    : []
  const maxImp = importancias[0]?.[1] ?? 1

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Modelo preditivo (Fase 6)</h1>
          <div className="sub">
            Random Forest exportada para JSON e servida com inferência Python pura no serverless
          </div>
        </div>
      </div>

      {erro && <div className="card mb"><p className="error">{erro}</p></div>}

      <div className="grid cols-4 mb">
        <div className="card">
          <div className="label">Acurácia</div>
          <div className="value">{metrics ? (metrics.accuracy * 100).toFixed(1) + '%' : '—'}</div>
        </div>
        <div className="card">
          <div className="label">ROC AUC</div>
          <div className="value">{metrics ? metrics.roc_auc.toFixed(3) : '—'}</div>
        </div>
        <div className="card">
          <div className="label">Árvores</div>
          <div className="value">{health?.modelo.n_arvores ?? '—'}</div>
        </div>
        <div className="card">
          <div className="label">Regras NLP (Fase 2)</div>
          <div className="value">{health?.nlp.regras_ontologia ?? '—'}</div>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Importância das variáveis</h2>
          {importancias.map(([nome, v]) => (
            <div className="bar-row" key={nome}>
              <span className="name">{nome}</span>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${(v / maxImp) * 100}%` }} />
              </div>
              <span className="muted">{(v * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>

        <div className="card">
          <h2>Matriz de confusão (holdout)</h2>
          {metrics && (
            <table>
              <thead>
                <tr><th /><th>Prev. sem pico</th><th>Prev. pico</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><b>Real sem pico</b></td>
                  <td>{metrics.confusion_matrix[0][0]}</td>
                  <td>{metrics.confusion_matrix[0][1]}</td>
                </tr>
                <tr>
                  <td><b>Real pico</b></td>
                  <td>{metrics.confusion_matrix[1][0]}</td>
                  <td>{metrics.confusion_matrix[1][1]}</td>
                </tr>
              </tbody>
            </table>
          )}
          <p className="muted mt" style={{ fontSize: '0.8rem' }}>
            Treinado sobre base sintética balanceada (4000 amostras, seed=42) — ver <code>ml/</code>.
            A paridade entre o <code>predict_proba</code> do scikit-learn e a inferência
            pura-Python foi verificada no export (delta &lt; 1e-9).
          </p>
        </div>
      </div>
    </>
  )
}
