import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { Card, Pill } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loading, ErrorBox } from "@/components/Loading";
import { fmt } from "@/lib/utils";
import { haptic } from "@/lib/tg";
import { toast } from "sonner";

export default function Product() {
  const { id } = useParams();
  const pid = Number(id);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["product", pid],
    queryFn: () => api.product(pid),
    enabled: Number.isFinite(pid),
  });
  const addMut = useMutation({
    mutationFn: () => api.cartAdd(pid, 1),
    onSuccess: () => {
      haptic("ok");
      toast.success("В корзине");
      qc.invalidateQueries({ queryKey: ["cart"] });
    },
    onError: (e: Error) => {
      haptic("err");
      toast.error(e.message);
    },
  });

  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorBox error={error} />;

  return (
    <div className="space-y-4">
      <Card className="p-0 overflow-hidden">
        {data.photo_url ? (
          <img src={data.photo_url} alt="" className="w-full aspect-[4/3] object-cover" />
        ) : (
          <div className="w-full aspect-[4/3] bg-neon-grad/30 flex items-center justify-center text-6xl">📦</div>
        )}
        <div className="p-4 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold neon-text">{data.name}</h1>
              <div className="text-xs text-muted-foreground mt-0.5">🏙 {data.city_name}</div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-neon-soft">{fmt(data.price_usdt)}</div>
              <div className="text-xs text-muted-foreground">USDT</div>
            </div>
          </div>
          {data.description && (
            <p className="text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">
              {data.description}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Pill>📦 {data.stock < 0 ? "Бесконечно" : `${data.stock} в наличии`}</Pill>
            {data.is_active ? <Pill>✅ Активен</Pill> : <Pill className="bg-destructive/15 text-destructive-foreground border-destructive/30">⛔ Неактивен</Pill>}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-3">
        <Button
          variant="primary"
          size="lg"
          disabled={addMut.isPending || data.stock === 0 || !data.is_active}
          onClick={() => addMut.mutate()}
        >
          {addMut.isPending ? "..." : "🧺 В корзину"}
        </Button>
        <Button variant="secondary" size="lg" onClick={() => navigate("/cart")}>
          Перейти в корзину
        </Button>
      </div>
    </div>
  );
}
