import { useRef } from 'react'

/** Mantém o valor anterior quando a resposta nova veio vazia (evita piscar na UI). */
export function sticky<T>(next: T, prev: T, isEmpty: (v: T) => boolean = defaultEmpty): T {
  return isEmpty(next) ? prev : next
}

function defaultEmpty<T>(v: T): boolean {
  if (Array.isArray(v)) return v.length === 0
  return v == null
}

/** Descarta respostas de polls antigos que chegam fora de ordem. */
export function usePollRequestId() {
  const id = useRef(0)
  const begin = () => ++id.current
  const isLatest = (requestId: number) => requestId === id.current
  return { begin, isLatest }
}
