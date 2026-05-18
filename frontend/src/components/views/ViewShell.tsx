// Общий layout для pre-built views: PageHeader сверху, отступ-контент.
// Не путать с charts/ChartShell (тот — wrapper для single chart).

import type { ReactNode } from "react";
import { PageHeader } from "@/components/primitives/Primitives";
import { FilterBar } from "@/components/filters/FilterBar";
import styles from "./ViewShell.module.css";

export interface ViewShellProps {
  breadcrumbs: string[];
  title: ReactNode;
  sub?: string;
  right?: ReactNode;
  children: ReactNode;
}

export function ViewShell({ breadcrumbs, title, sub, right, children }: ViewShellProps) {
  return (
    <div className={styles.screen}>
      <PageHeader breadcrumbs={breadcrumbs} title={title} sub={sub} right={right} />
      <FilterBar />
      <div className={styles.body}>{children}</div>
    </div>
  );
}
