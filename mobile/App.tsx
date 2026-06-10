import { useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { StatusBar } from 'expo-status-bar'
import { cores } from './src/theme'
import LoginScreen from './src/screens/LoginScreen'
import DashboardScreen from './src/screens/DashboardScreen'
import ChatScreen from './src/screens/ChatScreen'

type Aba = 'dashboard' | 'chat'

export default function App() {
  const [usuario, setUsuario] = useState<string | null>(null)
  const [aba, setAba] = useState<Aba>('dashboard')

  if (!usuario) {
    return (
      <>
        <StatusBar style="light" />
        <LoginScreen onLogin={setUsuario} />
      </>
    )
  }

  return (
    <View style={styles.shell}>
      <StatusBar style="light" />
      <View style={styles.header}>
        <Text style={styles.brand}>🫀 CardioIA</Text>
        <Pressable onPress={() => setUsuario(null)}>
          <Text style={styles.sair}>Sair</Text>
        </Pressable>
      </View>

      {aba === 'dashboard' ? <DashboardScreen usuario={usuario} /> : <ChatScreen />}

      <View style={styles.tabs}>
        <Pressable
          style={[styles.tab, aba === 'dashboard' && styles.tabAtiva]}
          onPress={() => setAba('dashboard')}
        >
          <Text style={[styles.tabTexto, aba === 'dashboard' && styles.tabTextoAtivo]}>📊 Dados cardíacos</Text>
        </Pressable>
        <Pressable
          style={[styles.tab, aba === 'chat' && styles.tabAtiva]}
          onPress={() => setAba('chat')}
        >
          <Text style={[styles.tabTexto, aba === 'chat' && styles.tabTextoAtivo]}>💬 Assistente</Text>
        </Pressable>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  shell: { flex: 1, backgroundColor: cores.bg },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 52,
    paddingHorizontal: 18,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: cores.borda,
  },
  brand: { color: cores.texto, fontSize: 20, fontWeight: '700' },
  sair: { color: cores.textoDim, fontSize: 14 },
  tabs: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: cores.borda,
    backgroundColor: '#0a0f1b',
  },
  tab: { flex: 1, paddingVertical: 14, alignItems: 'center' },
  tabAtiva: { borderTopWidth: 2, borderTopColor: cores.primaria },
  tabTexto: { color: cores.textoDim, fontSize: 14, fontWeight: '600' },
  tabTextoAtivo: { color: cores.texto },
})
