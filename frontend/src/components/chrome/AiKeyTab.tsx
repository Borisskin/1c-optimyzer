import { useEffect, useState } from "react";
import { backend } from "@/api/backend";
import type { AiSettingsState } from "@/api/backend";
import styles from "./SettingsDialog.module.css";

/**
 * Вкладка «AI» — ключ Anthropic пользователя (BYOK).
 *
 * Ключ принадлежит пользователю и хранится только на его машине; вызовы идут
 * напрямую в Anthropic, минуя какие-либо наши серверы. Поэтому здесь же честно
 * сказано, что платит за запросы он сам — это снимает вопросы к биллингу.
 *
 * Введённый ключ обратно не показывается никогда — только маска.
 */
export function AiKeyTab() {
  const [state, setState] = useState<AiSettingsState | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const refresh = async () => {
    try {
      setState(await backend.aiSettingsGet());
    } catch (e) {
      console.warn("[ai] не удалось прочитать настройки", e);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const save = async () => {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const res = await backend.aiSettingsSetKey(input.trim());
      if (!res.ok) {
        setError(res.error ?? "Не удалось сохранить ключ");
        return;
      }
      setInput("");
      setSaved(true);
      await refresh();
    } catch (e) {
      setError("Не удалось сохранить ключ");
      console.warn("[ai] save failed", e);
    } finally {
      setBusy(false);
    }
  };

  const clear = async () => {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await backend.aiSettingsClearKey();
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.aiTab}>
      <p className={styles.description}>
        AI-разбор запросов, планов и регрессий работает на вашем ключе Anthropic.
        Ключ хранится только на этом компьютере, запросы идут напрямую в Anthropic —
        мы их не видим и не посредничаем. Оплата запросов — по вашему тарифу Anthropic.
      </p>

      <div className={styles.aiStatusRow}>
        <span className={state?.has_key ? styles.aiOn : styles.aiOff}>
          {state?.has_key ? "AI подключён" : "AI не настроен"}
        </span>
        {state?.has_key && <code className={styles.aiMask}>{state.key_masked}</code>}
      </div>

      <label className={styles.aiLabel} htmlFor="ai-key">
        {state?.has_key ? "Заменить ключ" : "Ключ Anthropic"}
      </label>
      <div className={styles.aiRow}>
        <input
          id="ai-key"
          type="password"
          className={styles.aiInput}
          placeholder="sk-ant-..."
          value={input}
          autoComplete="off"
          spellCheck={false}
          onChange={(e) => {
            setInput(e.target.value);
            setError(null);
            setSaved(false);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && input.trim() && !busy) void save();
          }}
        />
        <button
          type="button"
          className={styles.btnPrimary}
          disabled={!input.trim() || busy}
          onClick={() => void save()}
        >
          {busy ? "Сохраняю…" : "Сохранить"}
        </button>
        {state?.has_key && (
          <button
            type="button"
            className={styles.btnSecondary}
            disabled={busy}
            onClick={() => void clear()}
          >
            Удалить
          </button>
        )}
      </div>

      {error && <p className={styles.aiError}>{error}</p>}
      {saved && <p className={styles.aiSaved}>Ключ сохранён — AI готов к работе.</p>}

      <p className={styles.aiHint}>
        Ключ можно создать в консоли Anthropic:{" "}
        <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noreferrer">
          console.anthropic.com
        </a>
      </p>
    </div>
  );
}
