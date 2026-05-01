declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        initDataUnsafe?: { user?: { id: number; username?: string; first_name?: string; last_name?: string } };
        ready(): void;
        expand(): void;
        setHeaderColor?: (c: string) => void;
        setBackgroundColor?: (c: string) => void;
        themeParams?: Record<string, string>;
        BackButton?: { show(): void; hide(): void; onClick(cb: () => void): void; offClick(cb: () => void): void };
        HapticFeedback?: { impactOccurred(t: "light" | "medium" | "heavy" | "rigid" | "soft"): void; notificationOccurred(t: "error" | "success" | "warning"): void };
        showAlert?: (msg: string) => void;
        showConfirm?: (msg: string, cb: (ok: boolean) => void) => void;
      };
    };
  }
}

export const tg = (typeof window !== "undefined" && window.Telegram?.WebApp) || undefined;

export function initTelegram() {
  if (!tg) return;
  try {
    tg.ready();
    tg.expand();
    tg.setHeaderColor?.("#0a0911");
    tg.setBackgroundColor?.("#0a0911");
  } catch {
    /* ignore */
  }
}

export function getInitData(): string {
  return tg?.initData ?? "";
}

export function haptic(kind: "tap" | "ok" | "err" = "tap") {
  if (!tg) return;
  try {
    if (kind === "tap") tg.HapticFeedback?.impactOccurred("light");
    else if (kind === "ok") tg.HapticFeedback?.notificationOccurred("success");
    else if (kind === "err") tg.HapticFeedback?.notificationOccurred("error");
  } catch {
    /* ignore */
  }
}
