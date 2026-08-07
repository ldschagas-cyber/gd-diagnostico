import { useCallback, useRef, useState } from "react";

/** Toast simples (compartilhado entre telas) — mesmo padrão dos wireframes
 * aprovados: mensagem some sozinha depois de 3s. */
export function useToast() {
  const [msg, setMsg] = useState("");
  const [show, setShow] = useState(false);
  const timer = useRef(null);

  const showToast = useCallback((texto) => {
    setMsg(texto);
    setShow(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setShow(false), 3000);
  }, []);

  return { msg, show, showToast };
}

export default function Toast({ msg, show }) {
  return (
    <div className={`toast${show ? " show" : ""}`} role="status" aria-live="polite">
      {msg}
    </div>
  );
}
