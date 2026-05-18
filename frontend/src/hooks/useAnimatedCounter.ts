import { useEffect, useRef, useState } from "react";

interface State {
  displayed: number;
  baseValue: number;
  baseTime: number;
  ratePerMs: number;
  rafId: number;
}

/**
 * Плавно докручивает монотонно растущий счётчик между редкими backend-tick'ами.
 *
 * Backend шлёт прогресс раз в ~250 мс (throttled), поэтому без интерполяции
 * счётчик стоит на месте по 200+ мс — UI выглядит зависшим. Хук считает
 * скорость по двум последним реальным значениям и докручивает displayed
 * через requestAnimationFrame (~60 fps) до момента следующего реального tick'а.
 *
 * При active=false возвращает target без анимации.
 */
export function useAnimatedCounter(target: number, active: boolean): number {
  const [displayed, setDisplayed] = useState(target);
  const ref = useRef<State>({
    displayed: target,
    baseValue: target,
    baseTime: typeof performance !== "undefined" ? performance.now() : 0,
    ratePerMs: 0,
    rafId: 0,
  });

  useEffect(() => {
    const r = ref.current;
    const now = performance.now();
    const dt = now - r.baseTime;
    const dv = target - r.baseValue;

    if (dv < 0) {
      r.displayed = target;
      r.ratePerMs = 0;
      setDisplayed(target);
    } else if (dt > 50 && dv > 0) {
      const instant = dv / dt;
      r.ratePerMs = r.ratePerMs === 0 ? instant : r.ratePerMs * 0.4 + instant * 0.6;
    }

    r.baseValue = target;
    r.baseTime = now;
    if (r.displayed < target) {
      r.displayed = target;
      setDisplayed(target);
    }
  }, [target]);

  useEffect(() => {
    if (!active) {
      ref.current.displayed = target;
      setDisplayed(target);
      return;
    }

    const tick = () => {
      const r = ref.current;
      const sinceBase = performance.now() - r.baseTime;
      const projection = r.baseValue + r.ratePerMs * Math.min(sinceBase, 1200);
      if (r.displayed < projection) {
        const step = Math.max(1, r.ratePerMs * 16);
        r.displayed = Math.min(projection, r.displayed + step);
        setDisplayed(r.displayed);
      }
      r.rafId = requestAnimationFrame(tick);
    };

    ref.current.rafId = requestAnimationFrame(tick);
    return () => {
      if (ref.current.rafId) cancelAnimationFrame(ref.current.rafId);
    };
  }, [active, target]);

  return displayed;
}
