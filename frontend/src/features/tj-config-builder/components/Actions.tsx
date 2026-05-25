/**
 * Sprint 10 — Actions: только кнопка «Сбросить настройки».
 * Кнопка сохранения файла перенесена в шапку XmlPreview —
 * там она рядом с тем XML, который пользователь видит и редактирует.
 */
import styles from "./Actions.module.css";

interface Props {
  onReset: () => void;
}

export function Actions({ onReset }: Props) {
  return (
    <div className={styles.root}>
      <button
        className={styles.btn_reset}
        onClick={onReset}
        title="Сбросить все настройки к значениям по умолчанию"
      >
        Сбросить настройки
      </button>
    </div>
  );
}
