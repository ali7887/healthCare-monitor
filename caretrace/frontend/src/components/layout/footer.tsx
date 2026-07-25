/**
 * Global footer with the designer branding element. Rendered at the bottom of
 * the dashboard layout's scroll container, so it appears on every view without
 * ever overlapping active UI.
 */
export function Footer() {
  return (
    <footer className="mt-auto border-t bg-card/50">
      <div className="mx-auto w-full max-w-7xl px-4 py-4 sm:px-6">
        <p className="text-center text-xs text-muted-foreground">
          Designed &amp; Built by{" "}
          <a
            href="https://alikiani.vercel.app"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium underline-offset-4 transition-colors hover:text-primary hover:underline"
          >
            Ali Kiani
          </a>
        </p>
      </div>
    </footer>
  );
}
