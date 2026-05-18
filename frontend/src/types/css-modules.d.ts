// Global type declaration for CSS Modules.
// Vite handles the runtime; TypeScript needs this hint so `import styles from
// "./Foo.module.css"` doesn't error in IDE / `tsc --noEmit`.

declare module "*.module.css" {
  const classes: Readonly<Record<string, string>>;
  export default classes;
}
