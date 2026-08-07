import { api } from "./client";

export async function getOportunidades() {
  const { data } = await api.get("/oportunidades");
  return data;
}

export async function priorizarOportunidade(id) {
  const { data } = await api.patch(`/oportunidades/${id}/priorizar`);
  return data;
}
