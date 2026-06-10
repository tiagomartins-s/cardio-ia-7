import { useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { cores } from '../theme'

export default function LoginScreen({ onLogin }: { onLogin: (nome: string) => void }) {
  const [nome, setNome] = useState('')
  const [erro, setErro] = useState('')

  function entrar() {
    if (nome.trim().length < 2) {
      setErro('Informe seu nome para entrar.')
      return
    }
    onLogin(nome.trim())
  }

  return (
    <View style={styles.wrap}>
      <Text style={styles.logo}>🫀</Text>
      <Text style={styles.titulo}>CardioIA</Text>
      <Text style={styles.sub}>Plataforma de Inteligência Cardíaca Total</Text>

      <View style={styles.card}>
        <Text style={styles.label}>Nome</Text>
        <TextInput
          style={styles.input}
          value={nome}
          onChangeText={setNome}
          placeholder="Como devemos te chamar?"
          placeholderTextColor={cores.textoDim}
        />
        {erro ? <Text style={styles.erro}>{erro}</Text> : null}
        <Pressable style={styles.botao} onPress={entrar}>
          <Text style={styles.botaoTexto}>Entrar na plataforma</Text>
        </Pressable>
      </View>

      <Text style={styles.aviso}>MVP acadêmico (FIAP — Fase 7). Não substitui atendimento médico.</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: cores.bg, alignItems: 'center', justifyContent: 'center', padding: 24 },
  logo: { fontSize: 56 },
  titulo: { color: cores.texto, fontSize: 30, fontWeight: '800', marginTop: 6 },
  sub: { color: cores.textoDim, fontSize: 13, marginBottom: 28 },
  card: {
    width: '100%',
    backgroundColor: cores.card,
    borderColor: cores.borda,
    borderWidth: 1,
    borderRadius: 14,
    padding: 20,
  },
  label: { color: cores.textoDim, fontSize: 12, marginBottom: 6 },
  input: {
    backgroundColor: cores.card2,
    borderColor: cores.borda,
    borderWidth: 1,
    borderRadius: 9,
    color: cores.texto,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 14,
  },
  erro: { color: cores.alto, marginBottom: 10, fontSize: 13 },
  botao: { backgroundColor: cores.primaria, borderRadius: 9, paddingVertical: 13, alignItems: 'center' },
  botaoTexto: { color: '#fff', fontWeight: '700', fontSize: 15 },
  aviso: { color: cores.textoDim, fontSize: 11, marginTop: 22, textAlign: 'center' },
})
