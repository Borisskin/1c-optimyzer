// Sprint 2 Phase A stub.
// OQL DSL удалён; SQL Engine + Editor + Templates появляются в Phase B.
// Этот файл сейчас держит роут `sql` рабочим: показывает live progress
// при загрузке архива и базовый summary когда архив готов.

import { useEffect } from "react";
import { Icon } from "@/components/icons/Icon";
import { Badge, PageHeader } from "@/components/primitives/Primitives";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import { useAnimatedCounter } from "@/hooks/useAnimatedCounter";
import styles from "./SQLConsole.module.css";

export function SQLConsoleScreen({ onLoadArchive }: { onLoadArchive: () => void }) {
  const archive = useAppStore((s) => s.archive);
  const setLastResult = useAppStore((s) => s.setLastResult);

  // Legacy lastResult из OQL execution более не релевантен.
  useEffect(() => {
    setLastResult(null);
  }, [setLastResult]);

  const ready = archive?.status === "ready";

  return (
    <div className={styles.screen}>
      <PageHeader
        breadcrumbs={[t.sql.breadcrumb, t.sql.pageTitle]}
        title={
          <span className={styles.title_inline}>
            {t.sql.pageTitle} <Badge tone="mute">{t.sql.sprintLabel}</Badge>
          </span>
        }
        sub={t.sql.description}
      />

      <div className={styles.workarea} style={{ gridTemplateColumns: "1fr" }}>
        <section className={styles.results_pane}>
          {!ready && <EmptyState onLoadArchive={onLoadArchive} archive={archive} />}
          {ready && archive && <ReadyStub eventsCount={archive.events_parsed} />}
        </section>
      </div>
    </div>
  );
}

function ReadyStub({ eventsCount }: { eventsCount: number }) {
  return (
    <div className={styles.empty}>
      <Icon name="Database" size={26} color="var(--o-accent)" />
      <div className={styles.empty_title}>{t.sql.results.empty.ready}</div>
      <div className={styles.empty_events}>{eventsCount.toLocaleString("ru-RU")}</div>
      <div className={styles.empty_sub}>{t.sql.results.empty.readyHint}</div>
    </div>
  );
}

function EmptyState({
  onLoadArchive,
  archive,
}: {
  onLoadArchive: () => void;
  archive: ReturnType<typeof useAppStore.getState>["archive"];
}) {
  const ingest = useAppStore((s) => s.ingest);
  const isParsing =
    archive && archive.status !== "ready" && archive.status !== "error";
  const ingestActive = Boolean(ingest && ingest.phase !== "done" && ingest.phase !== "error");

  const liveEvents = useAnimatedCounter(
    ingest?.events_inserted ?? archive?.events_parsed ?? 0,
    Boolean(isParsing) && ingestActive,
  );
  const liveBytes = useAnimatedCounter(
    ingest?.bytes_done ?? 0,
    Boolean(isParsing) && ingestActive,
  );

  if (isParsing) {
    const verbMap: Record<string, string> = {
      extracting: t.sql.archiveLoading.extracting,
      discovering: t.sql.archiveLoading.discovering,
      parsing: t.sql.archiveLoading.parsing,
      indexing: t.sql.archiveLoading.indexing,
    };
    const verb = verbMap[archive.status] ?? t.sql.archiveLoading.parsing;
    const bytesTotal = ingest?.bytes_total ?? archive.size_bytes ?? 0;
    const percent =
      bytesTotal > 0
        ? Math.min(100, (liveBytes / bytesTotal) * 100)
        : archive.progress * 100;
    return (
      <div className={styles.empty}>
        <Icon name="Refresh" size={22} color="var(--o-accent)" className="pulse" />
        <div className={styles.empty_title}>{verb}</div>
        <div className={styles.empty_events}>
          {Math.floor(liveEvents).toLocaleString("ru-RU")}
        </div>
        <div className={styles.empty_sub}>
          {t.statusbar.events} · {percent.toFixed(1)}%
        </div>
        <div className={styles.progress}>
          <div className={styles.progress_fill} style={{ width: `${percent}%` }} />
        </div>
      </div>
    );
  }
  if (archive && archive.status === "error") {
    return (
      <div className={styles.empty}>
        <Icon name="AlertTriangle" size={22} color="var(--o-err)" />
        <div className={styles.empty_title}>{t.sql.archiveError.title}</div>
        <div className={styles.empty_sub}>{archive.errors[0] || t.sql.archiveError.unknown}</div>
        <button className={styles.empty_btn} onClick={onLoadArchive}>
          <Icon name="Upload" size={13} /> {t.sql.archiveError.chooseAnother}
        </button>
      </div>
    );
  }
  return (
    <div className={styles.empty}>
      <Icon name="Database" size={26} color="var(--o-text-3)" />
      <div className={styles.empty_title}>{t.sql.results.empty.noArchive}</div>
      <div className={styles.empty_sub}>{t.sql.results.empty.hint}</div>
      <button className={styles.empty_btn} onClick={onLoadArchive}>
        <Icon name="Upload" size={13} /> {t.sql.results.empty.loadButton}
      </button>
    </div>
  );
}
