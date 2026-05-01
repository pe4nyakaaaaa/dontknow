import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Loading, ErrorBox, Empty } from "@/components/Loading";
import { PageHeader } from "@/components/Header";
import { fmt, fmtDate } from "@/lib/utils";

const STATUS_COLOR: Record<string, string> = {
  IN_DELIVERY: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  DELIVERED: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
};

export default function CourierPage() {
  const q = useQuery({ queryKey: ["courier-orders"], queryFn: api.courierOrders, refetchInterval: 8000 });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  if (!q.data?.length) return <Empty title="Заказов нет" hint="Когда появится — придёт уведомление" icon="🚴" />;
  return (
    <div className="space-y-3">
      <PageHeader title="Курьер" subtitle="Активные заказы" />
      {q.data.map((o) => (
        <Link key={o.id} to={`/orders/${o.id}`}>
          <Card className="space-y-1 hover:border-neon/60 transition-colors">
            <div className="flex justify-between">
              <div className="font-semibold">#{o.id} · {o.product_name}</div>
              <span className={`text-[10px] rounded-full border px-2 py-0.5 ${STATUS_COLOR[o.status] ?? ""}`}>{o.status}</span>
            </div>
            <div className="text-xs text-muted-foreground">🏙 {o.city_name} · {fmt(o.total_usdt)} USDT · {fmtDate(o.created_at)}</div>
            <div className="text-sm">📍 {o.delivery_address}</div>
          </Card>
        </Link>
      ))}
    </div>
  );
}
