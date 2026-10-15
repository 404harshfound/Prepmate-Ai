import type { ReactNode } from "react";

/** A full-page message on the ruled sheet: loading, errors, not found. */
export function PageStatus({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl items-center px-4 py-16">
      <div className="sheet w-full pr-4" role="status" aria-live="polite">
        <h1 className="sheet-title">{title}</h1>
        {children ? <div className="rules-1 text-graphite">{children}</div> : null}
      </div>
    </main>
  );
}
