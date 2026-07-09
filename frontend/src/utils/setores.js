/**
 * Setores (segmentos econômicos) dos embarcadores.
 *
 * Espelha exatamente os valores do `SetorEnum` do backend
 * (app/domain/entities). É a fonte única para o Select de cadastro de empresa
 * e estará disponível para filtros, dashboards e benchmark setorial futuros.
 * Manter sincronizado com o backend ao incluir novos setores.
 */
export const SETORES = [
  "Indústria",
  "Distribuidor",
  "Atacado",
  "Varejo",
  "E-commerce",
  "Transportadora",
  "Operador Logístico",
  "Agronegócio",
  "Saúde",
  "Farmacêutico",
  "Alimentício",
  "Automotivo",
  "Construção Civil",
  "Químico",
  "Têxtil",
  "Papel e Celulose",
  "Metalurgia",
  "Tecnologia",
  "Outros",
];

export default SETORES;
