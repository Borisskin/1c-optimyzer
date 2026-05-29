/**
 * useRemoteConfig — опрашивает GET /v1/config при старте и раз в ~6 часов.
 *
 * Успешный ответ → кладём в configStore (+ localStorage). Ошибка/сервер
 * недоступен → молча работаем на последнем известном конфиге (graceful).
 * Тех-детали — только в console, не в UI.
 */

import { useEffect } from "react";
import { cloud } from "@/api/cloud";
import { useConfigStore } from "@/store/configStore";

const POLL_PERIOD_MS = 6 * 60 * 60 * 1000; // 6 часов

async function fetchOnce(): Promise<void> {
  try {
    const cfg = await cloud.getRemoteConfig();
    useConfigStore.getState().setConfig(cfg);
  } catch (e) {
    // Сервер недоступен — остаёмся на последнем известном конфиге.
    console.warn("[remote-config] не удалось получить конфиг, работаем на кеше:", e);
  }
}

export function useRemoteConfig() {
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const tick = () => {
      if (cancelled) return;
      void fetchOnce();
      timer = setTimeout(tick, POLL_PERIOD_MS);
    };

    // Первый опрос вскоре после старта (даём приложению инициализироваться).
    timer = setTimeout(tick, 2000);

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);
}
