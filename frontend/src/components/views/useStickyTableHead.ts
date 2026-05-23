// Хук для правильной работы sticky panel_head + thead в ViewShell-таблицах.
//
// Проблема: panel_head sticky top:0, а thead sticky top:N. Если N не равен
// реальной высоте panel_head, получается:
//   - N меньше → thead заезжает на panel_head
//   - N больше → между ними щель, через которую видны скроллящиеся строки
//   - В Excel заголовки прилеплены без щелей и непрозрачные — мы хотим то же
//
// Решение: ResizeObserver измеряет высоту panel_head, выставляет CSS-переменную
// --sticky-head-h на родителе .panel, thead читает её в `top`. В ViewShell.module.css
// .table th { top: var(--sticky-head-h, 44px) } — fallback 44px на случай если
// hook ещё не успел замерить (первый кадр).
//
// Использование:
//   const { panelHeadRef, panelStyle } = useStickyTableHead<HTMLDivElement>();
//   <div className={vshellStyles.panel} style={panelStyle}>
//     <div ref={panelHeadRef} className={vshellStyles.panel_head}>...</div>
//     <table>...</table>
//   </div>

import { useEffect, useRef, useState } from "react";
import type { CSSProperties, RefObject } from "react";

export interface StickyTableHead<T extends HTMLElement> {
  panelHeadRef: RefObject<T>;
  panelStyle: CSSProperties;
}

export function useStickyTableHead<T extends HTMLElement>(): StickyTableHead<T> {
  const panelHeadRef = useRef<T>(null);
  const [height, setHeight] = useState(44);

  useEffect(() => {
    const el = panelHeadRef.current;
    if (!el) return;

    const update = () => {
      const h = el.getBoundingClientRect().height;
      // Round up чтобы не было sub-pixel щели; min 32 чтобы fallback не уехал
      // в 0 если ref в момент измерения ещё не отрендерился.
      setHeight(Math.max(32, Math.ceil(h)));
    };

    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const panelStyle: CSSProperties = {
    // CSS-переменная читается из .table th в ViewShell.module.css. Каст к any
    // потому что React.CSSProperties не знает про custom properties.
    ["--sticky-head-h" as string]: `${height}px`,
  };

  return { panelHeadRef, panelStyle };
}
