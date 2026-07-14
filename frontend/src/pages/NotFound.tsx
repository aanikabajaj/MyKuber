import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/Logo";

export function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 aurora">
      <Logo />
      <div className="text-center">
        <div className="text-7xl font-extrabold text-primary">404</div>
        <p className="mt-2 text-muted-foreground">This page could not be authenticated into existence.</p>
      </div>
      <Link to="/">
        <Button>Back to safety</Button>
      </Link>
    </div>
  );
}
