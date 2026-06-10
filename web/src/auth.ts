// Autenticação simplificada do MVP: sessão local (localStorage).
// Em produção seria substituída por um IdP (ex.: Auth0/Cognito/Firebase Auth).

const KEY = "cardioia_user";

export interface Usuario {
  nome: string;
  perfil: "medico" | "paciente";
}

export function usuarioAtual(): Usuario | null {
  const raw = localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Usuario;
  } catch {
    return null;
  }
}

export function login(nome: string, perfil: Usuario["perfil"]): Usuario {
  const u: Usuario = { nome, perfil };
  localStorage.setItem(KEY, JSON.stringify(u));
  return u;
}

export function logout(): void {
  localStorage.removeItem(KEY);
}
