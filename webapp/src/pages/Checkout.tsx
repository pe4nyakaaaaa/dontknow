import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading, ErrorBox } from "@/components/Loading";
import { PageHeader } from "@/components/Header";
import { fmt } from "@/lib/utils";
import { haptic } from "@/lib/tg";
import { toast } from "sonner";

export default function Checkout() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const cartQ = useQuery({ queryKey: ["cart"], queryFn: api.cart });
  const meQ = useQuery({ queryKey: ["me"], queryFn: api.me });
  const [addresses, setAddresses] = useState<Record<number, string>>({});
  const [method, setMethod] = useState<"BALANCE" | "TON" | "USDT_TRC20">("BALANCE");

  const cityIds = Array.from(new Set((cartQ.data?.items || []).map((i) => i.city_id)));
  const cityNames = Object.fromEntries((cartQ.data?.items || []).map((i) => [i.city_id, i.city_name]));

  useEffect(() => {
    if (!meQ.data || !cartQ.data) return;
    if ((meQ.data.balance_usdt || 0) < (cartQ.data.total_usdt || 0)) setMethod("TON");
  }, [meQ.data, cartQ.data]);

  const checkoutMut = useMutation({
    mutationFn: () =>
      api.checkout({
        method,
        addresses: cityIds.map((cid) => ({ city_id: cid, address: addresses[cid] || "" })),
      }),
    onSuccess: (res) => {
      haptic("ok");
      qc.invalidateQueries({ queryKey: ["cart"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      qc.invalidateQueries({ queryKey: ["orders"] });
      if (res.paid_from_balance) {
        toast.success(`Заказ оформлен (#${res.order_ids.join(", #")})`);
        navigate(`/orders/${res.order_ids[0]}`);
      } else {
        toast.success("Создан платёж — переведите крипту");
        navigate(`/orders/${res.order_ids[0]}`);
      }
    },
    onError: (e: Error) => {
      haptic("err");
      toast.error(e.message);
    },
  });

  if (cartQ.isLoading || meQ.isLoading) return <Loading />;
  if (cartQ.error) return <ErrorBox error={cartQ.error} />;
  if (!cartQ.data?.items.length) {
    return (
      <div>
        <PageHeader title="Оформление" />
        <Card>Корзина пуста.</Card>
      </div>
    );
  }

  const balance = meQ.data?.balance_usdt || 0;
  const total = cartQ.data.total_usdt;
  const canBalance = balance >= total;
  const allAddressed = cityIds.every((cid) => (addresses[cid] || "").trim().length >= 5);

  return (
    <div className="space-y-4">
      <PageHeader title="Оформление" subtitle="Адрес и оплата" />

      <Card className="space-y-3">
        <div className="text-sm font-semibold">📍 Адреса доставки</div>
        {cityIds.map((cid) => (
          <div key={cid} className="space-y-1">
            <div className="text-xs text-muted-foreground">🏙 {cityNames[cid]}</div>
            <Input
              placeholder="Улица, дом, квартира, ориентир"
              value={addresses[cid] || ""}
              onChange={(e) => setAddresses({ ...addresses, [cid]: e.target.value })}
            />
          </div>
        ))}
      </Card>

      <Card className="space-y-2">
        <div className="text-sm font-semibold">💳 Способ оплаты</div>
        <PaymentChoice
          active={method === "BALANCE"}
          disabled={!canBalance}
          onClick={() => setMethod("BALANCE")}
          title={`💼 С баланса · ${fmt(balance)} USDT`}
          desc={canBalance ? "Мгновенно, без подтверждения" : "Не хватает на балансе"}
        />
        <PaymentChoice
          active={method === "TON"}
          onClick={() => setMethod("TON")}
          title="💎 TON"
          desc="С подтверждением админом"
        />
        <PaymentChoice
          active={method === "USDT_TRC20"}
          onClick={() => setMethod("USDT_TRC20")}
          title="🪙 USDT (TRC-20)"
          desc="С подтверждением админом"
        />
      </Card>

      <Card className="space-y-1">
        <div className="flex justify-between text-sm">
          <div>Товары</div>
          <div className="font-medium">{fmt(cartQ.data.items_total_usdt)} USDT</div>
        </div>
        <div className="flex justify-between text-sm">
          <div>Доставка</div>
          <div className="font-medium">{fmt(cartQ.data.delivery_total_usdt)} USDT</div>
        </div>
        <div className="border-t border-border my-2" />
        <div className="flex justify-between">
          <div className="font-semibold">Итого</div>
          <div className="text-xl font-bold text-neon-soft">{fmt(total)} USDT</div>
        </div>
      </Card>

      <Button size="lg" className="w-full" disabled={!allAddressed || checkoutMut.isPending} onClick={() => checkoutMut.mutate()}>
        {checkoutMut.isPending ? "..." : method === "BALANCE" ? "⚡ Оплатить с баланса" : "💎 Создать платёж"}
      </Button>
    </div>
  );
}

function PaymentChoice({
  active, disabled, onClick, title, desc,
}: { active: boolean; disabled?: boolean; onClick: () => void; title: string; desc: string }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`w-full text-left rounded-xl px-3 py-2.5 border transition-all flex items-center justify-between gap-2 ${
        active ? "border-neon bg-neon/15 shadow-neon" : "border-border bg-background/40 hover:border-neon/50"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <div>
        <div className="font-medium">{title}</div>
        <div className="text-xs text-muted-foreground">{desc}</div>
      </div>
      {active && <span className="text-neon-soft">●</span>}
    </button>
  );
}
