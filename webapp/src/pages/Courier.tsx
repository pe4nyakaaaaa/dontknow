import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, type CourierOrder } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loading, ErrorBox, Empty } from "@/components/Loading";
import { PageHeader } from "@/components/Header";
import { fmt, fmtDate } from "@/lib/utils";

const STATUS_COLOR: Record<string, string> = {
  PAID: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  IN_DELIVERY: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  DELIVERED: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
};

function OrderCard({ o, onTake, taking }: { o: CourierOrder; onTake?: () => void; taking?: boolean }) {
  return (
    <Card className="space-y-1">
      <div className="flex justify-between">
        <Link to={`/orders/${o.id}`} className="font-semibold hover:text-neon">
          #{o.id} · {o.product_name}
        </Link>
        <span className={`text-[10px] rounded-full border px-2 py-0.5 ${STATUS_COLOR[o.status] ?? ""}`}>{o.status}</span>
      </div>
      <div className="text-xs text-muted-foreground">🏙 {o.city_name} · {fmt(o.total_usdt)} USDT · {fmtDate(o.created_at)}</div>
      {o.delivery_address && <div className="text-sm">📍 {o.delivery_address}</div>}
      {!o.is_mine && o.status === "PAID" && onTake && (
        <Button variant="success" className="w-full mt-2" disabled={taking} onClick={onTake}>
          {taking ? "Беру…" : "✅ Принять заказ"}
        </Button>
      )}
    </Card>
  );
}

export default function CourierPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["courier-orders"], queryFn: api.courierOrders, refetchInterval: 8000 });

  const takeMut = useMutation({
    mutationFn: (id: number) => api.courierTake(id),
    onSuccess: () => {
      toast.success("Заказ взят");
      qc.invalidateQueries({ queryKey: ["courier-orders"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const orders = q.data ?? [];
  const available = orders.filter((o) => !o.is_mine);
  const mine = orders.filter((o) => o.is_mine);

  if (!orders.length) return <Empty title="Заказов нет" hint="Когда появится — придёт уведомление" icon="🚴" />;

  return (
    <div className="space-y-4">
      <PageHeader title="Курьер" subtitle="Активные заказы" />
      {available.length > 0 && (
        <section className="space-y-2">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">Доступные · {available.length}</div>
          {available.map((o) => (
            <OrderCard
              key={o.id}
              o={o}
              onTake={() => takeMut.mutate(o.id)}
              taking={takeMut.isPending && takeMut.variables === o.id}
            />
          ))}
        </section>
      )}
      {mine.length > 0 && (
        <section className="space-y-2">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">Мои заказы · {mine.length}</div>
          {mine.map((o) => (
            <OrderCard key={o.id} o={o} />
          ))}
        </section>
      )}
    </div>
  );
}
