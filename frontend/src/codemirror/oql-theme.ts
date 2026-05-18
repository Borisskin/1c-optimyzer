import { EditorView } from "@codemirror/view";

export const oqlEditorTheme = EditorView.theme({
  "&": {
    height: "100%",
    fontSize: "13px",
    fontFamily: "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace",
    background: "#FBFBFA",
    color: "#1F2937",
  },
  ".cm-content": {
    padding: "12px 16px",
    caretColor: "#0F766E",
  },
  ".cm-line": {
    padding: "0 2px",
    lineHeight: "1.6",
  },
  "&.cm-focused": {
    outline: "none",
  },
  ".cm-gutters": {
    background: "#FBFBFA",
    color: "#A3A3A3",
    border: "none",
    borderRight: "1px solid #E5E5E5",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: "12px",
  },
  ".cm-activeLineGutter": {
    color: "#0F766E",
    background: "transparent",
  },
  ".cm-activeLine": {
    background: "rgba(15, 118, 110, 0.04)",
  },
  ".cm-selectionBackground, ::selection": {
    background: "#A7F3D0 !important",
  },
  ".cm-tooltip": {
    background: "#FFFFFF",
    border: "1px solid #E5E5E5",
    borderRadius: "8px",
    fontSize: "12px",
    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
  },
  ".cm-tooltip-autocomplete > ul > li": {
    padding: "4px 10px",
  },
  ".cm-tooltip-autocomplete > ul > li[aria-selected]": {
    background: "#0F766E",
    color: "#FFFFFF",
  },
  ".cm-diagnostic-error": {
    borderLeft: "3px solid #DC2626",
  },
  ".cm-lintRange-error": {
    backgroundImage: "none",
    borderBottom: "1px wavy #DC2626",
  },
});
