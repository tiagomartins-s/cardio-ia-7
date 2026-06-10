import { useCallback, useEffect, useState } from 'react'
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native'
import { api, type Health, type LeituraIot, type PredicaoHistorico } from '../api'
import { cores, corStatus } from '../theme'

const POLL_MS = 6000

export default function DashboardScreen({ usuario }: { usuario: string }) {
  const [leituras, setLeituras] = useState<LeituraIot[]>([])
  const [predicoes, setPredicoes] = useState<PredicaoHistorico[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [erro, setErro] = useState('')
  const [atualizando, setAtualizando] = useState(false)

  const carregar = useCallback(async () => {
    try {
      const [l, p, h] = await Promise.all([api.leiturasIot(20), api.predicoes(5), api.health()])
      setLeituras(l)
      setPredicoes(p)
      setHealth(h)
      setErro('')
    } catch (e) {
      setErro(`Sem conexão com a API: ${String(e)}`)
    }
  }, [])

  useEffect(() => {
    carregar()
    const t = setInterval(carregar, POLL_MS)
    return () => clearInterval(t)
  }, [carregar])

  const ultima = leituras[0]

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={{ padding: 16, gap: 12 }}
      refreshControl={
        <RefreshControl
          refreshing={atualizando}
          onRefresh={async () => {
            setAtualizando(true)
            await carregar()
            setAtualizando(false)
          }}
          tintColor={cores.texto}
        />
      }
    >
      <Text style={styles.ola}>Olá, {usuario} 👋</Text>
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {health ? (
        <Text style={styles.apiOk}>
          ● API online — modelo {health.modelo.carregado ? `RF ${health.modelo.n_arvores} árvores` : 'heurístico'}
        </Text>
      ) : null}

      <View style={styles.linha}>
        <View style={styles.cardMetrica}>
          <Text style={styles.label}>BPM (sensor)</Text>
          <Text style={[styles.valor, { color: corStatus(ultima?.status_edge) }]}>
            {ultima?.bpm ?? '—'}
          </Text>
        </View>
        <View style={styles.cardMetrica}>
          <Text style={styles.label}>Temp. paciente</Text>
          <Text style={styles.valor}>{ultima?.temperatura_pac ?? '—'}°C</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitulo}>📡 Leituras do dispositivo (Wokwi)</Text>
        {leituras.length === 0 ? (
          <Text style={styles.dim}>Nenhuma leitura recebida ainda.</Text>
        ) : (
          leituras.slice(0, 8).map((l) => (
            <View key={l.id} style={styles.item}>
              <Text style={styles.dim}>#{l.id}</Text>
              <Text style={styles.itemTexto}>
                {l.bpm ?? '—'} bpm · {l.temperatura_amb ?? '—'}°C · {l.umidade ?? '—'}%
              </Text>
              <Text style={[styles.statusTag, { color: corStatus(l.avaliacao?.status_servidor) }]}>
                {l.avaliacao?.status_servidor ?? l.status_edge ?? '—'}
              </Text>
            </View>
          ))
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitulo}>🤖 Predições recentes da IA</Text>
        {predicoes.length === 0 ? (
          <Text style={styles.dim}>Nenhuma predição registrada.</Text>
        ) : (
          predicoes.map((p) => (
            <View key={p.id} style={styles.predicao}>
              <View style={styles.item}>
                <Text style={styles.itemTexto}>{p.payload.nome ?? 'anônimo'}</Text>
                <Text style={[styles.statusTag, { color: corStatus(p.classificacao) }]}>
                  {p.classificacao} · {(p.probabilidade * 100).toFixed(0)}%
                </Text>
              </View>
              <Text style={styles.dim} numberOfLines={2}>{p.payload.recomendacao_final}</Text>
            </View>
          ))
        )}
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  ola: { color: cores.texto, fontSize: 18, fontWeight: '700' },
  apiOk: { color: cores.ok, fontSize: 12 },
  erro: { color: cores.alto, fontSize: 13 },
  linha: { flexDirection: 'row', gap: 12 },
  cardMetrica: {
    flex: 1,
    backgroundColor: cores.card,
    borderColor: cores.borda,
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    alignItems: 'center',
  },
  card: {
    backgroundColor: cores.card,
    borderColor: cores.borda,
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    gap: 8,
  },
  cardTitulo: { color: cores.texto, fontWeight: '700', fontSize: 15, marginBottom: 4 },
  label: { color: cores.textoDim, fontSize: 12 },
  valor: { color: cores.texto, fontSize: 30, fontWeight: '800' },
  item: { flexDirection: 'row', alignItems: 'center', gap: 10, justifyContent: 'space-between' },
  itemTexto: { color: cores.texto, fontSize: 13, flex: 1 },
  statusTag: { fontSize: 12, fontWeight: '800' },
  predicao: { gap: 2, borderBottomColor: cores.borda, borderBottomWidth: StyleSheet.hairlineWidth, paddingBottom: 8 },
  dim: { color: cores.textoDim, fontSize: 12 },
})
