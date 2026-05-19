import { ViewShell } from "@/components/views/ViewShell";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

// Sprint 3 Phase D — наполнится после ITS-spec parser + synthetic fixture.
export function DeadlockAnatomyScreen({ archiveId }: Props) {
  return (
    <ViewShell
      breadcrumbs={["Анализ", "Анатомия дедлока"]}
      title={<>Анатомия дедлока</>}
      sub="Drill-down по TDEADLOCK событию — будет наполнен в Phase D"
    >
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.empty}>
          {archiveId ? "Phase D in progress" : "Загрузите архив"}
        </div>
      </div>
    </ViewShell>
  );
}
