import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/Header";
import { Loading, ErrorBox, Empty } from "@/components/Loading";
import { fmt } from "@/lib/utils";

export function CatalogCities() {
  const { data, isLoading, error } = useQuery({ queryKey: ["cities"], queryFn: api.cities });
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data?.length) return <Empty title="Пока нет городов" hint="Загляните позже" icon="🏙" />;
  return (
    <div className="space-y-4">
      <PageHeader title="Города" subtitle="Выберите свой регион" />
      <div className="grid gap-3">
        {data.map((c) => (
          <Link key={c.id} to={`/catalog/${c.id}`}>
            <Card className="flex items-center justify-between gap-3 hover:border-neon/60 transition-colors">
              <div>
                <div className="text-lg font-semibold">🏙 {c.name}</div>
                <div className="text-xs text-muted-foreground">
                  {c.products_count} товаров · доставка {fmt(c.delivery_price_usdt)} USDT
                </div>
              </div>
              <div className="text-neon-soft text-2xl">→</div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function CatalogProducts() {
  const { cityId } = useParams();
  const navigate = useNavigate();
  const id = Number(cityId);
  const { data, isLoading, error } = useQuery({
    queryKey: ["city-products", id],
    queryFn: () => api.cityProducts(id),
    enabled: Number.isFinite(id),
  });
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  return (
    <div className="space-y-3">
      <PageHeader title={data?.[0]?.city_name || "Товары"} subtitle="Карточки товаров" />
      {!data?.length ? (
        <Empty title="В этом городе пока пусто" icon="🛍" />
      ) : (
        <div className="grid gap-3">
          {data.map((p) => (
            <Card
              key={p.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/product/${p.id}`)}
              onKeyDown={(e) => e.key === "Enter" && navigate(`/product/${p.id}`)}
              className="cursor-pointer flex items-center gap-3 hover:border-neon/60 transition-colors"
            >
              {p.photo_url ? (
                <img src={p.photo_url} alt="" className="w-16 h-16 rounded-xl object-cover border border-border" />
              ) : (
                <div className="w-16 h-16 rounded-xl bg-neon/15 border border-neon/30 flex items-center justify-center text-2xl">📦</div>
              )}
              <div className="flex-1 min-w-0">
                <div className="font-semibold truncate">{p.name}</div>
                <div className="text-xs text-muted-foreground line-clamp-1">{p.description || "Нажмите, чтобы увидеть подробности"}</div>
              </div>
              <div className="text-right">
                <div className="text-base font-bold text-neon-soft">{fmt(p.price_usdt)} USDT</div>
                <div className="text-[10px] text-muted-foreground">
                  {p.stock < 0 ? "∞" : p.stock} в наличии
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
