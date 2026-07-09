/**
 * Persistência de ESTADO DE TELA entre navegações.
 *
 * O React Query cuida do cache dos DADOS do servidor. Ele NÃO guarda o estado
 * de interface (filtros, busca, paginação, ordenação, aba selecionada, itens
 * expandidos, posição do scroll). Estes hooks resolvem essa parte, para que ao
 * voltar a uma tela ela apareça exatamente como estava.
 *
 * Armazenamento: sessionStorage — sobrevive à navegação entre telas e ao F5,
 * e é limpo quando a aba do navegador é fechada (comportamento desejado: cada
 * sessão de trabalho começa limpa, mas navegar não perde o contexto).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

const PREFIXO = "gd_tela_";

function ler(chave, inicial) {
  try {
    const bruto = sessionStorage.getItem(PREFIXO + chave);
    return bruto ? { ...inicial, ...JSON.parse(bruto) } : inicial;
  } catch {
    return inicial;
  }
}

function gravar(chave, valor) {
  try {
    sessionStorage.setItem(PREFIXO + chave, JSON.stringify(valor));
  } catch {
    /* sessionStorage cheio/indisponível — ignora, degrada para estado só em memória */
  }
}

/**
 * Estado de tela persistente.
 *
 * @param {string} chave  identificador único da tela (ex.: "transportadoras").
 * @param {object} inicial estado inicial (filtros, busca, paginação...).
 * @returns [estado, setEstado, patch] — `patch(parcial)` faz merge raso.
 */
export function useTelaEstado(chave, inicial = {}) {
  const [estado, setEstado] = useState(() => ler(chave, inicial));

  useEffect(() => {
    gravar(chave, estado);
  }, [chave, estado]);

  const patch = useCallback(
    (parcial) =>
      setEstado((atual) => ({
        ...atual,
        ...(typeof parcial === "function" ? parcial(atual) : parcial),
      })),
    []
  );

  return [estado, setEstado, patch];
}

/**
 * Restaura a posição de rolagem da janela ao voltar para a tela e a salva
 * continuamente. Use uma vez, no topo da página. A chave padrão é a rota atual.
 */
export function useScrollRestaurar(chave) {
  const location = useLocation();
  const id = PREFIXO + "scroll_" + (chave || location.pathname);

  useEffect(() => {
    const salvo = Number(sessionStorage.getItem(id));
    if (salvo) {
      // aguarda o conteúdo renderizar antes de rolar
      const t = requestAnimationFrame(() => window.scrollTo(0, salvo));
      return () => cancelAnimationFrame(t);
    }
  }, [id]);

  useEffect(() => {
    let raf = 0;
    const aoRolar = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() =>
        sessionStorage.setItem(id, String(window.scrollY))
      );
    };
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => {
      window.removeEventListener("scroll", aoRolar);
      cancelAnimationFrame(raf);
    };
  }, [id]);
}

/**
 * Estado persistente pronto para o DataGrid do MUI: paginação, ordenação,
 * filtro e colunas visíveis. Devolve o objeto `props` para espalhar no
 * <DataGrid {...gridProps} />.
 */
export function useDataGridEstado(chave, inicial = {}) {
  const [estado, , patch] = useTelaEstado(`grid_${chave}`, {
    paginationModel: { page: 0, pageSize: 25 },
    sortModel: [],
    filterModel: { items: [] },
    columnVisibilityModel: {},
    ...inicial,
  });

  const props = {
    paginationModel: estado.paginationModel,
    onPaginationModelChange: (paginationModel) => patch({ paginationModel }),
    sortModel: estado.sortModel,
    onSortModelChange: (sortModel) => patch({ sortModel }),
    filterModel: estado.filterModel,
    onFilterModelChange: (filterModel) => patch({ filterModel }),
    columnVisibilityModel: estado.columnVisibilityModel,
    onColumnVisibilityModelChange: (columnVisibilityModel) =>
      patch({ columnVisibilityModel }),
  };

  return { estado, patch, props };
}

const useTelaEstadoDefault = useTelaEstado;
export default useTelaEstadoDefault;
