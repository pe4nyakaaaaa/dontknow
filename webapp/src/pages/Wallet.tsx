import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type PaymentOut } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading, ErrorBox, Empty } from "@/components/Loading";
import { PageHeader } from "@/components/Header";
import { fmt, fmtDate } from "@/lib/utils";
import { haptic } from "@/lib/tg";
import { toast } from "sonner";

export default function Wallet() {
  const qc = useQueryClient();
  const meQ = useQuery({ queryKey: ["me"], queryFn: api.me });
  const paymentsQ = useQuery({ queryKey: ["payments"], queryFn: api.walletPayments });
  const addrQ = useQuery({ queryKey: ["wallet-addr"], queryFn: api.walletAddresses });

  const [amount, setAmount] = useState("50");
  const [method, setMethod] = useState<"TON" | "USDT_TRC20">("TON");
  const [pending, setPending] = useState<PaymentOut | null>(null);
  const [tx, setTx] = useState("");

  const startMut = useMutation({
    mutationFn: () => api.walletTopup(parseFloat(amount), method),
    onSuccess: (p) => {
      haptic("ok");
      setPending(p);
      qc.invalidateQueries({ queryKey: ["payments"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const submitMut = useMutation({
    mutationFn: () => api.walletSubmitTx(pending!.id, tx),
    onSuccess: () => {
      toast.success("TX отправлен. Ждём подтверждения.");
      haptic("ok");
      setPending(null);
      setTx("");
      qc.invalidateQueries({ queryKey: ["payments"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (meQ.isLoading) return <Loading />;
  if (meQ.error) return <ErrorBox error={meQ.error} />;

  const wallet = method === "TON" ? addrQ.data?.TON : addrQ.data?.USDT_TRC20;

  return (
    <div className="space-y-4">
      <PageHeader title="Кошелёк" subtitle="Баланс и пополнения" />

      <Card className="bg-neon-grad text-white relative overflow-hidden">
        <div className="absolute -right-12 -top-12 w-44 h-44 rounded-full bg-white/30 blur-3xl pointer-events-none" />
        <div className="text-xs uppercase tracking-widest opacity-80">Доступно</div>
        <div className="text-4xl font-extrabold">
          {fmt(meQ.data?.balance_usdt || 0)} <span className="text-base font-semibold opacity-80">USDT</span>
        </div>
        <div className="mt-2 text-sm opacity-80">
          🎁 Бесплатных заказов: <b>{meQ.data?.free_credits ?? 0}</b>
        </div>
      </Card>

      {!pending ? (
        <Card className="space-y-3">
          <div className="text-sm font-semibold">➕ Пополнить</div>
          <div className="flex gap-2">
            {[25, 50, 100, 250].map((v) => (
              <Button key={v} variant={amount === String(v) ? "primary" : "secondary"} size="sm" className="flex-1" onClick={() => setAmount(String(v))}>
                {v}
              </Button>
            ))}
          </div>
          <Input
            type="number"
            inputMode="decimal"
            min="1"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Сумма USDT"
          />
          <div className="grid grid-cols-2 gap-2">
            <Button variant={method === "TON" ? "primary" : "secondary"} onClick={() => setMethod("TON")}>
              💎 TON
            </Button>
            <Button variant={method === "USDT_TRC20" ? "primary" : "secondary"} onClick={() => setMethod("USDT_TRC20")}>
              🪙 USDT TRC-20
            </Button>
          </div>
          <Button size="lg" className="w-full" disabled={startMut.isPending || !parseFloat(amount)} onClick={() => startMut.mutate()}>
            {startMut.isPending ? "..." : "Создать платёж"}
          </Button>
        </Card>
      ) : (
        <Card className="space-y-3">
          <div className="text-sm font-semibold">💸 Переведите {fmt(pending.amount_usdt)} USDT</div>
          <div className="text-xs text-muted-foreground">{pending.method === "TON" ? "Сеть TON" : "Сеть TRC-20"}</div>
          <div className="rounded-xl bg-input border border-border p-3 break-all text-xs font-mono">
            {wallet || "—"}
          </div>
          <Input placeholder="TX-хэш / Hash" value={tx} onChange={(e) => setTx(e.target.value)} />
          <div className="grid grid-cols-2 gap-2">
            <Button variant="secondary" onClick={() => setPending(null)}>Отмена</Button>
            <Button disabled={!tx || submitMut.isPending} onClick={() => submitMut.mutate()}>
              {submitMut.isPending ? "..." : "Отправить TX"}
            </Button>
          </div>
        </Card>
      )}

      <Card>
        <div className="text-sm font-semibold mb-2">📜 История пополнений</div>
        {paymentsQ.isLoading ? (
          <div className="text-xs text-muted-foreground">Загрузка...</div>
        ) : !paymentsQ.data?.length ? (
          <Empty title="Пусто" hint="Здесь будут ваши пополнения" icon="📜" />
        ) : (
          <div className="space-y-2">
            {paymentsQ.data.map((p) => (
              <div key={p.id} className="flex items-center justify-between text-sm rounded-xl border border-border p-2">
                <div>
                  <div className="font-medium">#{p.id} · {p.kind} · {p.method}</div>
                  <div className="text-[11px] text-muted-foreground">{fmtDate(p.created_at)}</div>
                </div>
                <div className="text-right">
                  <div className="font-semibold">{fmt(p.amount_usdt)} USDT</div>
                  <StatusPill status={p.status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    PENDING_PAYMENT: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    PENDING_VERIFY: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    CONFIRMED: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    REJECTED: "bg-destructive/15 text-destructive-foreground border-destructive/30",
  };
  const label: Record<string, string> = {
    PENDING_PAYMENT: "ожидает TX",
    PENDING_VERIFY: "проверка",
    CONFIRMED: "подтверждено",
    REJECTED: "отклонено",
  };
  return (
    <span className={`inline-block text-[10px] rounded-full border px-2 py-0.5 ${map[status] ?? ""}`}>
      {label[status] ?? status}
    </span>
  );
}
