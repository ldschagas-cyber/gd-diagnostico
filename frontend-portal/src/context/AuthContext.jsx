import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as authApi from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | authenticated | anonymous

  useEffect(() => {
    // Sem token em JS pra checar antes — se não houver cookie válido,
    // /auth/me simplesmente falha (mesmo padrão do painel interno).
    authApi
      .me()
      .then((data) => {
        setUsuario(data);
        setStatus("authenticated");
      })
      .catch(() => setStatus("anonymous"));
  }, []);

  const login = useCallback(async (email, senha) => {
    await authApi.login(email, senha);
    const data = await authApi.me();
    setUsuario(data);
    setStatus("authenticated");
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // cookies já expiram sozinhos; ignora falha de rede no logout
    }
    setUsuario(null);
    setStatus("anonymous");
  }, []);

  return (
    <AuthContext.Provider value={{ usuario, status, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}
