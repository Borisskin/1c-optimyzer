/**
 * Sprint 6 Phase E — отображение диагностик от bsl-language-server.
 *
 * Showcases the production-grade SDBL analyzer (19 rules) — Pro/Business
 * tier feature. Structured cards с severity, range, AI explanation.
 *
 * Q6 решение архитектора: показываем grouped diagnostics (overlapping
 * соединяются в одну card). Q7: все 19 правил activated by default.
 */

import { useMemo } from "react";
import type {
  BslLsAnalyzeResult,
  BslLsDiagnostic,
  BslLsDiagnosticGroup,
  BslLsSeverity,
} from "@/api/backend";
import styles from "./BslLsFindings.module.css";

interface Props {
  result: BslLsAnalyzeResult | null;
  loading: boolean;
  onSelectRange?: (startLine: number, startChar: number, endLine: number, endChar: number) => void;
}

const SEVERITY_LABELS: Record<BslLsSeverity, string> = {
  Blocker: "БЛОКЕР",
  Critical: "КРИТИЧНО",
  Major: "ВАЖНО",
  Minor: "МИНОР",
  Info: "ИНФО",
};

const SEVERITY_CLASS: Record<BslLsSeverity, string> = {
  Blocker: styles.sevBlocker,
  Critical: styles.sevCritical,
  Major: styles.sevMajor,
  Minor: styles.sevMinor,
  Info: styles.sevInfo,
};

const RULE_TITLES: Record<string, string> = {
  QueryParseError: "Синтаксическая ошибка SDBL",
  QueryToMissingMetadata: "Запрос к несуществующему объекту конфигурации",
  VirtualTableCallWithoutParameters: "Виртуальная таблица без параметров",
  FieldsFromJoinsWithoutIsNull: "Поле из LEFT JOIN без ЕСТЬNULL",
  JoinWithSubQuery: "JOIN с подзапросом",
  JoinWithVirtualTable: "JOIN с виртуальной таблицей",
  RefOveruse: "Лишнее .Ссылка в цепочке полей",
  QueryNestedFieldsByDot: "Разыменование ссылочного поля через точку",
  FullOuterJoinQuery: "ПОЛНОЕ соединение",
  UnionAll: "ОБЪЕДИНИТЬ вместо ОБЪЕДИНИТЬ ВСЕ",
  SelectTopWithoutOrderBy: "ВЫБРАТЬ ПЕРВЫЕ без УПОРЯДОЧИТЬ ПО",
  IncorrectUseLikeInQuery: "Некорректное использование ПОДОБНО",
  LogicalOrInJoinQuerySection: "ИЛИ в условии соединения",
  LogicalOrInTheWhereSectionOfQuery: "ИЛИ в секции ГДЕ",
  SameMetadataObjectAndChildNames: "Имя объекта совпадает с именем потомка",
  ForbiddenMetadataName: "Запрещённое имя объекта метаданных",
  AssignAliasFieldsInQuery: "Поле без псевдонима КАК",
  UsingLikeInQuery: "Использование ПОДОБНО",
  MultilineStringInQuery: "Многострочный литерал в запросе",
};

function ruleTitle(code: string): string {
  return RULE_TITLES[code] ?? code;
}

export function BslLsFindings({ result, loading, onSelectRange }: Props) {
  const groups = result?.grouped ?? [];

  const counts = useMemo(() => {
    const c = { Blocker: 0, Critical: 0, Major: 0, Minor: 0, Info: 0 };
    for (const g of groups) {
      c[g.severity] += 1;
    }
    return c;
  }, [groups]);

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Анализ запроса через bsl-language-server…</div>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  if (!result.ok) {
    return (
      <div className={styles.container}>
        <div className={styles.errorBox}>
          <div className={styles.errorTitle}>Не удалось проанализировать запрос</div>
          <div className={styles.errorDetail}>{result.error}</div>
          {result.hint && <div className={styles.errorHint}>{result.hint}</div>}
        </div>
      </div>
    );
  }

  const hasGrouped = groups.length > 0;
  const configHint =
    !result.configuration_connected && hasGrouped ? (
      <div className={styles.configHint}>
        💡 Подключите конфигурацию в Настройках для семантической проверки
        (имена справочников, реквизиты, виртуальные таблицы).
      </div>
    ) : null;

  return (
    <div className={styles.container}>
      <div className={styles.summaryBar}>
        <div className={styles.summaryLabel}>Найдено проблем:</div>
        <SeverityBadge severity="Blocker" count={counts.Blocker} />
        <SeverityBadge severity="Critical" count={counts.Critical} />
        <SeverityBadge severity="Major" count={counts.Major} />
        <SeverityBadge severity="Minor" count={counts.Minor} />
        <SeverityBadge severity="Info" count={counts.Info} />
        <div className={styles.timing}>
          {result.analysis_duration_ms} мс · bsl-LS {result.bsl_ls_version}
        </div>
      </div>

      {configHint}

      {!hasGrouped && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>✓</div>
          <div className={styles.emptyTitle}>Запрос выглядит хорошо</div>
          <div className={styles.emptySub}>
            bsl-language-server не нашёл проблем по {19} активным правилам.
          </div>
        </div>
      )}

      {hasGrouped && (
        <div className={styles.cards}>
          {groups.map((g, idx) => (
            <GroupCard key={idx} group={g} onSelectRange={onSelectRange} />
          ))}
        </div>
      )}
    </div>
  );
}

function SeverityBadge({ severity, count }: { severity: BslLsSeverity; count: number }) {
  if (count === 0) return null;
  return (
    <div className={`${styles.badge} ${SEVERITY_CLASS[severity]}`}>
      <span className={styles.badgeLabel}>{SEVERITY_LABELS[severity]}</span>
      <span className={styles.badgeCount}>{count}</span>
    </div>
  );
}

interface GroupCardProps {
  group: BslLsDiagnosticGroup;
  onSelectRange?: (startLine: number, startChar: number, endLine: number, endChar: number) => void;
}

function GroupCard({ group, onSelectRange }: GroupCardProps) {
  const { range, severity, codes, messages, snippet, primary } = group;
  const title = ruleTitle(primary.code);
  const isMultiCode = codes.length > 1;
  return (
    <div className={`${styles.card} ${SEVERITY_CLASS[severity]}`}>
      <div className={styles.cardHeader}>
        <div className={`${styles.cardBadge} ${SEVERITY_CLASS[severity]}`}>
          {SEVERITY_LABELS[severity]}
        </div>
        <div className={styles.cardTitle}>{title}</div>
        <button
          type="button"
          className={styles.cardJump}
          onClick={() =>
            onSelectRange?.(
              range.start.line,
              range.start.character,
              range.end.line,
              range.end.character,
            )
          }
          title="Перейти к строке в редакторе"
        >
          стр. {range.start.line + 1}:{range.start.character + 1}
        </button>
      </div>
      {snippet && (
        <pre className={styles.snippet}>
          <code>{snippet}</code>
        </pre>
      )}
      <ul className={styles.messageList}>
        {messages.map((m, i) => (
          <li key={i}>{m}</li>
        ))}
      </ul>
      {isMultiCode && (
        <div className={styles.codesRow}>
          <span className={styles.codesLabel}>Правила:</span>
          {codes.map((c) => (
            <code key={c} className={styles.codeChip}>
              {c}
            </code>
          ))}
        </div>
      )}
    </div>
  );
}
