/**
 * Sprint 8 Phase B — Settings tab «PostgreSQL Connections».
 *
 * Управление opt-in PG connections для re-EXPLAIN feature. Юзер может:
 *  - Добавить новое connection (имя/host/port/db/user/password)
 *  - Тест соединения (без сохранения)
 *  - Удалить
 *  - Назначить default
 *
 * Password хранится в OS keychain (Windows Credential Manager) — backend
 * управляет полностью. UI никогда не показывает password.
 */

import { useCallback, useEffect, useState } from "react";
import { backend, type PgConnectionPublic } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import styles from "./PgConnectionsTab.module.css";

type TestResult = {
  ok: boolean;
  message: string;
  version?: string;
};

export function PgConnectionsTab() {
  const [connections, setConnections] = useState<PgConnectionPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const pushToast = useAppStore((s) => s.pushToast);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await backend.pgListConnections();
      if (!resp.ok) {
        setError(resp.details ?? resp.error ?? "Не удалось загрузить список");
        return;
      }
      setConnections(resp.items ?? []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const onDelete = useCallback(
    async (id: number, name: string) => {
      // Используем confirm — destructive операция.
      // eslint-disable-next-line no-alert
      const ok = window.confirm(
        `Удалить подключение «${name}»? Пароль также будет удалён из OS keychain.`,
      );
      if (!ok) return;
      const resp = await backend.pgDeleteConnection(id);
      if (!resp.ok) {
        pushToast(`Ошибка удаления: ${resp.details ?? resp.error}`, "err");
        return;
      }
      pushToast("Подключение удалено", "info");
      await reload();
    },
    [pushToast, reload],
  );

  const onSetDefault = useCallback(
    async (id: number) => {
      const resp = await backend.pgSetDefault(id);
      if (!resp.ok) {
        pushToast(`Ошибка: ${resp.details ?? resp.error}`, "err");
        return;
      }
      await reload();
    },
    [pushToast, reload],
  );

  const onTest = useCallback(
    async (id: number, name: string) => {
      const resp = await backend.pgTestConnection(id);
      if (resp.ok) {
        pushToast(
          `${name}: подключение работает (${resp.version?.slice(0, 60) ?? "PostgreSQL"})`,
          "info",
        );
      } else {
        pushToast(
          `${name}: ${resp.details ?? resp.error ?? "не удалось подключиться"}`,
          "err",
        );
      }
    },
    [pushToast],
  );

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <div>
          <div className={styles.title}>PostgreSQL подключения</div>
          <div className={styles.subtitle}>
            Опционально. Нужны для интерактивной визуализации плана через pev2
            (re-EXPLAIN запросов из ТЖ архива). Используйте read-only
            пользователя — Optimyzer выполняет повторные EXPLAIN
            (FORMAT JSON, ANALYZE) для SELECT-запросов.
          </div>
        </div>
        <button
          type="button"
          className={styles.addBtn}
          onClick={() => setShowAddForm((v) => !v)}
        >
          {showAddForm ? "Отмена" : "+ Добавить"}
        </button>
      </div>

      {showAddForm && (
        <AddConnectionForm
          onCancel={() => setShowAddForm(false)}
          onSuccess={async () => {
            setShowAddForm(false);
            await reload();
            pushToast("Подключение сохранено", "info");
          }}
        />
      )}

      {error && <div className={styles.error}>{error}</div>}

      {loading ? (
        <div className={styles.loading}>Загрузка…</div>
      ) : connections.length === 0 ? (
        !showAddForm && (
          <div className={styles.empty}>
            Нет настроенных PostgreSQL подключений.
            <br />
            Нажмите «+ Добавить» чтобы создать первое.
          </div>
        )
      ) : (
        <div className={styles.list}>
          {connections.map((c) => (
            <div
              key={c.id}
              className={`${styles.card} ${c.is_default ? styles.cardDefault : ""}`}
            >
              <div className={styles.cardHeader}>
                <div className={styles.cardName}>
                  {c.name}
                  {c.is_default && (
                    <span className={styles.defaultBadge}>default</span>
                  )}
                </div>
                <div className={styles.cardActions}>
                  {!c.is_default && (
                    <button
                      type="button"
                      className={styles.actionBtn}
                      onClick={() => onSetDefault(c.id)}
                    >
                      Сделать default
                    </button>
                  )}
                  <button
                    type="button"
                    className={styles.actionBtn}
                    onClick={() => onTest(c.id, c.name)}
                  >
                    Проверить
                  </button>
                  <button
                    type="button"
                    className={styles.actionBtnDanger}
                    onClick={() => onDelete(c.id, c.name)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
              <div className={styles.cardMeta}>
                <span className={styles.metaItem}>
                  {c.username}@{c.host}:{c.port}/{c.database}
                </span>
                {c.last_used_at && (
                  <span className={styles.metaItem}>
                    использовалось: {formatRelative(c.last_used_at)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface AddFormProps {
  onCancel: () => void;
  onSuccess: () => void;
}

function AddConnectionForm({ onCancel, onSuccess }: AddFormProps) {
  const [name, setName] = useState("");
  const [host, setHost] = useState("localhost");
  const [port, setPort] = useState(5432);
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("postgres");
  const [password, setPassword] = useState("");
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onTest = useCallback(async () => {
    setTesting(true);
    setTestResult(null);
    setError(null);
    try {
      const resp = await backend.pgTestConnectionForm(
        host,
        port,
        database,
        username,
        password,
      );
      if (resp.ok) {
        setTestResult({
          ok: true,
          message: `Подключение работает ${
            resp.is_1c_build ? "(1С-сборка)" : ""
          }`,
          version: resp.version,
        });
      } else {
        setTestResult({
          ok: false,
          message: resp.details ?? resp.error ?? "Не удалось подключиться",
        });
      }
    } catch (e) {
      setTestResult({ ok: false, message: String(e) });
    } finally {
      setTesting(false);
    }
  }, [host, port, database, username, password]);

  const onSave = useCallback(async () => {
    if (!name.trim()) {
      setError("Укажите имя подключения");
      return;
    }
    if (!database.trim()) {
      setError("Укажите имя базы данных");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const resp = await backend.pgAddConnection(
        name.trim(),
        host.trim(),
        port,
        database.trim(),
        username.trim(),
        password,
      );
      if (!resp.ok) {
        setError(resp.details ?? resp.error ?? "Ошибка сохранения");
        return;
      }
      onSuccess();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }, [name, host, port, database, username, password, onSuccess]);

  return (
    <div className={styles.form}>
      <div className={styles.formTitle}>Новое подключение</div>
      <div className={styles.field}>
        <label className={styles.label}>Имя (для UI)</label>
        <input
          className={styles.input}
          type="text"
          placeholder="Production pgBase"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className={styles.row}>
        <div className={`${styles.field} ${styles.fieldGrow}`}>
          <label className={styles.label}>Host</label>
          <input
            className={styles.input}
            type="text"
            value={host}
            onChange={(e) => setHost(e.target.value)}
          />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Port</label>
          <input
            className={styles.input}
            type="number"
            min={1}
            max={65535}
            value={port}
            onChange={(e) => setPort(parseInt(e.target.value, 10) || 5432)}
          />
        </div>
      </div>
      <div className={styles.field}>
        <label className={styles.label}>Database</label>
        <input
          className={styles.input}
          type="text"
          placeholder="pgBase"
          value={database}
          onChange={(e) => setDatabase(e.target.value)}
        />
      </div>
      <div className={styles.row}>
        <div className={`${styles.field} ${styles.fieldGrow}`}>
          <label className={styles.label}>Username</label>
          <input
            className={styles.input}
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div className={`${styles.field} ${styles.fieldGrow}`}>
          <label className={styles.label}>Password</label>
          <input
            className={styles.input}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
        </div>
      </div>

      <div className={styles.hint}>
        Рекомендация: создайте отдельного PG пользователя только с правами SELECT —
        Optimyzer выполняет повторные EXPLAIN, для которых не нужны DML права.
        Пароль будет сохранён в OS keychain (Windows Credential Manager) —
        приложение не хранит его в plaintext.
      </div>

      {testResult && (
        <div
          className={
            testResult.ok ? styles.testResultOk : styles.testResultErr
          }
        >
          {testResult.message}
          {testResult.version && (
            <div className={styles.versionLine} title={testResult.version}>
              {testResult.version.split(" on ")[0]}
            </div>
          )}
        </div>
      )}

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.formActions}>
        <button
          type="button"
          className={styles.actionBtn}
          onClick={onTest}
          disabled={testing || saving}
        >
          {testing ? "Проверка…" : "Проверить"}
        </button>
        <button
          type="button"
          className={styles.actionBtn}
          onClick={onCancel}
          disabled={saving}
        >
          Отмена
        </button>
        <button
          type="button"
          className={styles.actionBtnPrimary}
          onClick={onSave}
          disabled={saving || testing}
        >
          {saving ? "Сохраняю…" : "Сохранить"}
        </button>
      </div>
    </div>
  );
}

function formatRelative(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
