import { useRef, useState } from 'react'
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { api } from '../api'
import { cores } from '../theme'

interface Msg {
  autor: 'user' | 'bot'
  texto: string
}

const SUGESTOES = [
  'Estou com dor no peito',
  'Quero agendar um eletrocardiograma',
  'Quais os sintomas de um infarto?',
]

export default function ChatScreen() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { autor: 'bot', texto: 'Olá! Sou a assistente virtual da CardioIA 🫀\nComo posso ajudar?' },
  ])
  const [sugestoes, setSugestoes] = useState<string[]>(SUGESTOES)
  const [texto, setTexto] = useState('')
  const [sessao, setSessao] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(false)
  const scrollRef = useRef<ScrollView>(null)

  async function enviar(t?: string) {
    const msg = (t ?? texto).trim()
    if (!msg || carregando) return
    setTexto('')
    setMsgs((m) => [...m, { autor: 'user', texto: msg }])
    setCarregando(true)
    try {
      const r = await api.chat(msg, sessao)
      setSessao(r.sessao_id)
      setMsgs((m) => [...m, { autor: 'bot', texto: r.resposta }])
      setSugestoes(r.sugestoes)
    } catch (e) {
      setMsgs((m) => [...m, { autor: 'bot', texto: `Erro ao falar com a API: ${String(e)}` }])
    } finally {
      setCarregando(false)
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100)
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.wrap}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView ref={scrollRef} style={styles.msgs} contentContainerStyle={{ padding: 14, gap: 8 }}>
        {msgs.map((m, i) => (
          <View key={i} style={[styles.msg, m.autor === 'user' ? styles.msgUser : styles.msgBot]}>
            <Text style={styles.msgTexto}>{m.texto}</Text>
          </View>
        ))}
        {carregando && (
          <View style={[styles.msg, styles.msgBot]}>
            <Text style={[styles.msgTexto, { color: cores.textoDim }]}>digitando…</Text>
          </View>
        )}
      </ScrollView>

      {sugestoes.length > 0 && (
        <ScrollView horizontal style={styles.chips} contentContainerStyle={{ gap: 8, paddingHorizontal: 12 }}>
          {sugestoes.map((s) => (
            <Pressable key={s} style={styles.chip} onPress={() => enviar(s)}>
              <Text style={styles.chipTexto}>{s}</Text>
            </Pressable>
          ))}
        </ScrollView>
      )}

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={texto}
          onChangeText={setTexto}
          placeholder="Escreva sua mensagem…"
          placeholderTextColor={cores.textoDim}
          onSubmitEditing={() => enviar()}
        />
        <Pressable style={styles.botao} onPress={() => enviar()}>
          <Text style={styles.botaoTexto}>➤</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  wrap: { flex: 1 },
  msgs: { flex: 1 },
  msg: { maxWidth: '80%', borderRadius: 14, paddingHorizontal: 12, paddingVertical: 9 },
  msgUser: { alignSelf: 'flex-end', backgroundColor: cores.primaria, borderBottomRightRadius: 4 },
  msgBot: { alignSelf: 'flex-start', backgroundColor: cores.card2, borderBottomLeftRadius: 4 },
  msgTexto: { color: cores.texto, fontSize: 14 },
  chips: { maxHeight: 44, marginBottom: 6 },
  chip: {
    borderColor: cores.borda,
    borderWidth: 1,
    backgroundColor: cores.card2,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  chipTexto: { color: cores.textoDim, fontSize: 12 },
  inputRow: { flexDirection: 'row', gap: 8, padding: 12, paddingTop: 4 },
  input: {
    flex: 1,
    backgroundColor: cores.card2,
    borderColor: cores.borda,
    borderWidth: 1,
    borderRadius: 9,
    color: cores.texto,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  botao: {
    backgroundColor: cores.primaria,
    borderRadius: 9,
    width: 46,
    alignItems: 'center',
    justifyContent: 'center',
  },
  botaoTexto: { color: '#fff', fontSize: 18 },
})
