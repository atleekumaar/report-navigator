import Link from "next/link";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-background text-slate-100 p-4">
      <div className="w-12 h-12 rounded-xl bg-accent/20 border border-accent/40 flex items-center justify-center mb-4">
        <Compass className="w-6 h-6 text-accent" />
      </div>
      <h2 className="text-xl font-bold mb-2">Page Not Found</h2>
      <p className="text-sm text-slate-400 mb-6 text-center max-w-sm">
        The requested report page or route does not exist.
      </p>
      <Link
        href="/"
        className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-medium transition-colors shadow-lg shadow-accent/20"
      >
        Return to Report Navigator
      </Link>
    </div>
  );
}

