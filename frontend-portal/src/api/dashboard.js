import { api } from "./client";

export async function getDashboard() {
  const { data } = await api.get("/dashboard");
  return data;
}
