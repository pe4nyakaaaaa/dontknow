import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ShoppingBag, Wallet, ScrollText, MessageSquareHeart, ShieldCheck, Truck, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardDesc, CardTitle, Pill } from "@/components/ui/card";
import { fmt } from "@/lib/utils";

export default function Home() {
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: api.me });

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden relative animate-glow">
        <div className="absolute -right-12 -top-12 w-44 h-44 rounded-full bg-neon-grad opacity-30 blur-3xl pointer-events-none" />
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 rounded-2xl bg-neon-grad flex items-center justify-center text-xl shadow-neon">🛒</div>
          <div>
            <div className="text-xs uppercase tracking-widest text-muted-foreground">Auto-Sales</div>
            <div className="text-xl font-bold">Привет, {me?.full_name || "гость"}</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-background/40 border border-border p-3">
            <div className="text-xs text-muted-foreground">Баланс</div>
            <div className="text-2xl font-bold text-neon-soft">{fmt(me?.balance_usdt || 0)} <span className="text-xs text-muted-foreground">USDT</span></div>
          </div>
          <div className="rounded-xl bg-background/40 border border-border p-3">
            <div className="text-xs text-muted-foreground">Бесплатных</div>
            <div className="text-2xl font-bold">{me?.free_credits ?? 0}</div>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-3">
        <Tile to="/catalog" icon={<ShoppingBag />} title="Каталог" desc="Города и товары" />
        <Tile to="/cart" icon={<Truck />} title="Корзина" desc="Оформить заказ" />
        <Tile to="/wallet" icon={<Wallet />} title="Кошелёк" desc="Пополнить TON / USDT" />
        <Tile to="/orders" icon={<ScrollText />} title="Заказы" desc="История и статус" />
        <Tile to="/reviews" icon={<MessageSquareHeart />} title="Отзывы" desc="Мнения покупателей" />
        {me?.is_admin && <Tile to="/admin" icon={<ShieldCheck />} title="Админка" desc="Города, товары, платежи" />}
        {me?.courier_city_id && <Tile to="/courier" icon={<Truck />} title="Курьер" desc="Активные заказы" />}
        {me?.is_moderator && <Tile to="/moderator" icon={<ShieldAlert />} title="Модератор" desc="Открытые диспуты" />}
      </div>

      <Card>
        <CardTitle className="mb-1">Как это работает</CardTitle>
        <CardDesc>
          Выберите город → товар → добавьте в корзину → оплатите с баланса в один клик или криптой.
          Курьер свяжется с вами через встроенный чат.
        </CardDesc>
        <div className="flex flex-wrap gap-2 mt-3">
          <Pill>⚡ Мгновенно с баланса</Pill>
          <Pill>🚴 Курьер на каждый город</Pill>
          <Pill>⚖️ Диспуты с модератором</Pill>
        </div>
      </Card>
    </div>
  );
}

function Tile({ to, icon, title, desc }: { to: string; icon: React.ReactNode; title: string; desc: string }) {
  return (
    <Link
      to={to}
      className="glass rounded-2xl p-4 hover:border-neon/60 transition-colors animate-fade-in"
    >
      <div className="w-10 h-10 rounded-xl bg-neon/15 border border-neon/25 flex items-center justify-center text-neon-soft mb-2">
        {icon}
      </div>
      <div className="font-semibold">{title}</div>
      <div className="text-xs text-muted-foreground">{desc}</div>
    </Link>
  );
}
