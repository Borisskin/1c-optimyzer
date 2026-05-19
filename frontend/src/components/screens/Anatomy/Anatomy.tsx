import { ViewShell } from "@/components/views/ViewShell";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

// Sprint 3 Phase C — содержательное наполнение прилетит в следующем коммите.
// Заглушка нужна чтобы Operations.tsx уже сейчас мог делать setScreen("anatomy").
export function AnatomyScreen({ archiveId }: Props) {
  return (
    <ViewShell
      breadcrumbs={["Анализ", "Анатомия операции"]}
      title={<>Анатомия операции</>}
      sub="Drill-down по операции из Бизнес-операций — будет наполнен в Phase C"
    >
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.empty}>
          {archiveId ? "Phase C in progress" : "Загрузите архив"}
        </div>
      </div>
    </ViewShell>
  );
}
