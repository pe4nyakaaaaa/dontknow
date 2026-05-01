import { Loader2 } from "lucide-react";

export function Loading({ label = "Загрузка..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
      <Loader2 className="w-7 h-7 animate-spin text-neon-soft" />
      <div className="text-sm">{label}</div>
    </div>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-xl border border-destructive/40 bg-destructive/10 text-destructive-foreground p-4 text-sm">
      ⚠️ {msg}
    </div>
  );
}

export function Empty({ icon, title, hint }: { icon?: React.ReactNode; title: string; hint?: string }) {
  return (
    <div className="text-center py-12">
      <div className="mx-auto mb-3 w-14 h-14 rounded-2xl glass flex items-center justify-center text-neon-soft">
        {icon ?? "📭"}
      </div>
      <div className="font-semibold">{title}</div>
      {hint && <div className="text-sm text-muted-foreground mt-1">{hint}</div>}
    </div>
  );
}
