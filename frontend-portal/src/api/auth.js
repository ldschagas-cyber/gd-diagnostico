import { api } from "./client";

export async function login(email, senha) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", senha);
  const { data } = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function me() {
  const { data } = await api.get("/auth/me");
  return data;
}

export async function logout() {
  await api.post("/auth/logout");
}
