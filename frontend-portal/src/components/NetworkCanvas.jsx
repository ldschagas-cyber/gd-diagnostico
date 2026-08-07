import { useEffect, useRef } from "react";

/** Rede de nós ambiente do palco de login — decorativa, mesma animação já
 * aprovada no wireframe (docs/specs/v6.18.0/v6.18.0_wireframe_portal_executivo_login.html). */
export default function NetworkCanvas() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let w, h, nodes, raf;
    const stageEl = canvas.parentElement;

    function resize() {
      const rect = stageEl.getBoundingClientRect();
      w = canvas.width = rect.width;
      h = canvas.height = rect.height;
    }
    function makeNodes() {
      const count = Math.max(16, Math.floor((w * h) / 38000));
      nodes = [];
      for (let i = 0; i < count; i++) {
        nodes.push({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - 0.5) * 0.14, vy: (Math.random() - 0.5) * 0.14, hub: Math.random() < 0.18 });
      }
    }
    function frame() {
      ctx.clearRect(0, 0, w, h);
      for (const n of nodes) {
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
      }
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dist = Math.hypot(a.x - b.x, a.y - b.y);
          const max = 150;
          if (dist < max) {
            ctx.strokeStyle = `rgba(199, 203, 224,${0.18 * (1 - dist / max)})`;
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
      }
      for (const n of nodes) {
        ctx.fillStyle = n.hub ? "rgba(201, 168, 76, 0.85)" : "rgba(76, 178, 222, 0.55)";
        ctx.beginPath(); ctx.arc(n.x, n.y, n.hub ? 2.6 : 1.5, 0, Math.PI * 2); ctx.fill();
      }
      raf = requestAnimationFrame(frame);
    }

    resize(); makeNodes();
    if (!reduceMotion) frame(); else ctx.clearRect(0, 0, w, h);

    function onResize() {
      cancelAnimationFrame(raf);
      resize(); makeNodes();
      if (!reduceMotion) frame(); else ctx.clearRect(0, 0, w, h);
    }
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden="true" />;
}
