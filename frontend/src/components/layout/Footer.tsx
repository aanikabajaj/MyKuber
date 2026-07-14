import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="border-t border-border/60 py-8">
      <div className="container flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
        <Logo />
        <p>© {new Date().getFullYear()} Punjab &amp; Sind Bank · IAARE Prototype</p>
        <p className="text-xs">Hackathon demonstration build — not a production banking system.</p>
      </div>
    </footer>
  );
}
