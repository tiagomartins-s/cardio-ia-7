export const cores = {
  bg: '#0c1220',
  card: '#131c2e',
  card2: '#1a2740',
  borda: '#24345a',
  texto: '#e7edf7',
  textoDim: '#94a3bf',
  primaria: '#e63956',
  ok: '#2dd4a7',
  atencao: '#f5b941',
  alto: '#f4564e',
  critico: '#e879f9',
  info: '#4f8ef7',
}

export function corStatus(s?: string | null): string {
  switch ((s ?? '').toUpperCase()) {
    case 'NORMAL':
    case 'BAIXO':
      return cores.ok
    case 'ATENCAO':
    case 'MODERADO':
    case 'MONITORAR':
      return cores.atencao
    case 'ALTO':
    case 'URGENTE':
      return cores.alto
    case 'CRITICO':
    case 'EMERGENCIA':
      return cores.critico
    default:
      return cores.info
  }
}
