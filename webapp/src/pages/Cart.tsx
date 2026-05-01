import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Minus, Trash2 } from "lucide-react";
import { api, type CartItemOut } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loading, ErrorBox, Empty } from "@/components/Loading";
import { PageHeader } from "@/components/Header";
import { fmt } from "@/lib/utils";
import { haptic } from "@/lib/tg";
import { toast } from "sonner";

export default function CartPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({ queryKey: ["cart"], queryFn: api.cart });

  const updateMut = useMutation({
    mutationFn: ({ id, quantity }: { id: number; quantity: number }) => api.cartUpdate(id, quantity),
    onSuccess: (cart) => {
      qc.setQueryData(["cart"], cart);
      haptic("tap");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const removeMut = useMutation({
    mutationFn: (id: number) => api.cartRemove(id),
    onSuccess: (cart) => qc.setQueryData(["cart"], cart),
  });

  const clearMut = useMutation({
    mutationFn: () => api.cartClear(),
    onSuccess: (cart) => qc.setQueryData(["cart"], cart),
  });

  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Корзина"
        subtitle={data?.items.length ? `${data.items.length} позиций` : "Пусто"}
        right={
          data?.items.length ? (
            <Button variant="ghost" size="sm" onClick={() => clearMut.mutate()}>
              <Trash2 className="w-4 h-4" /> Очистить
            </Button>
          ) : null
        }
      />
      {!data?.items.length ? (
        <Empty title="Корзина пуста" hint="Загляните в каталог" icon="🛒" />
      ) : (
        <>
          <div className="space-y-2">
            {data.items.map((it) => (
              <CartRow key={it.id} item={it} onChange={(q) => updateMut.mutate({ id: it.id, quantity: q })} onRemove={() => removeMut.mutate(it.id)} />
            ))}
          </div>
          <Card className="space-y-2">
            <Row label="🛍 Товары" value={`${fmt(data.items_total_usdt)} USDT`} />
            <Row label="🚚 Доставка" value={`${fmt(data.delivery_total_usdt)} USDT`} />
            <div className="border-t border-border my-2" />
            <Row label="Итого" value={`${fmt(data.total_usdt)} USDT`} bold />
          </Card>
          <Button size="lg" className="w-full" onClick={() => navigate("/checkout")}>
            ✨ Оформить заказ
          </Button>
          <div className="text-center text-xs text-muted-foreground">
            <Link to="/catalog" className="text-neon-soft hover:underline">Продолжить покупки</Link>
          </div>
        </>
      )}
    </div>
  );
}

function CartRow({ item, onChange, onRemove }: { item: CartItemOut; onChange: (q: number) => void; onRemove: () => void }) {
  return (
    <Card className="flex items-center gap-3">
      {item.photo_url ? (
        <img src={item.photo_url} alt="" className="w-14 h-14 rounded-xl object-cover border border-border" />
      ) : (
        <div className="w-14 h-14 rounded-xl bg-neon/15 border border-neon/30 flex items-center justify-center text-xl">📦</div>
      )}
      <div className="flex-1 min-w-0">
        <div className="font-semibold truncate">{item.product_name}</div>
        <div className="text-xs text-muted-foreground">🏙 {item.city_name}</div>
        <div className="text-sm text-neon-soft mt-0.5">{fmt(item.price_usdt)} USDT</div>
      </div>
      <div className="flex flex-col items-end gap-2">
        <div className="flex items-center gap-1.5">
          <Button variant="secondary" size="icon" onClick={() => onChange(item.quantity - 1)}>
            <Minus className="w-4 h-4" />
          </Button>
          <div className="w-7 text-center font-semibold">{item.quantity}</div>
          <Button variant="secondary" size="icon" onClick={() => onChange(item.quantity + 1)}>
            <Plus className="w-4 h-4" />
          </Button>
        </div>
        <button onClick={onRemove} className="text-xs text-muted-foreground hover:text-destructive">
          удалить
        </button>
      </div>
    </Card>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <div className={bold ? "font-semibold" : ""}>{label}</div>
      <div className={bold ? "text-base font-bold text-neon-soft" : "font-medium"}>{value}</div>
    </div>
  );
}
