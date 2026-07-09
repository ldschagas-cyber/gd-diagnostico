import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi } from "../api/endpoints";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(true);

  // Restaura a sessão a partir do cookie httpOnly (não há token em JS para
  // checar antes — se não houver cookie válido, /auth/me simplesmente falha).
  useEffect(() => {
    async function restaurar() {
      try {
        const me = await authApi.me();
        setUsuario(me);
      } catch {
        setUsuario(null);
      } finally {
        setCarregando(false);
      }
    }
    restaurar();
  }, []);

  const login = useCallback(async (email, senha) => {
    await authApi.login(email, senha);
    const me = await authApi.me();
    setUsuario(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUsuario(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ usuario, carregando, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
