import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Loading, ErrorBox, Empty } from "@/components/Loading";
import { PageHeader } from "@/components/Header";
import { fmtDate } from "@/lib/utils";

export default function Reviews() {
  const { data, isLoading, error } = useQuery({ queryKey: ["reviews"], queryFn: api.reviews });
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data?.length) return <Empty title="Отзывов пока нет" hint="Будьте первым" icon="💬" />;

  return (
    <div className="space-y-3">
      <PageHeader title="Отзывы" subtitle="Что говорят покупатели" />
      {data.map((r) => (
        <Card key={r.id} className="space-y-1">
          <div className="flex items-center justify-between">
            <div className="font-semibold">{r.user_name}</div>
            <div className="text-neon-soft drop-shadow-[0_0_8px_rgba(168,85,247,0.7)]">
              {"★".repeat(r.rating)}<span className="text-muted-foreground">{"★".repeat(5 - r.rating)}</span>
            </div>
          </div>
          <div className="text-[11px] text-muted-foreground">{fmtDate(r.created_at)}</div>
          {r.text && <div className="text-sm mt-1 whitespace-pre-wrap">{r.text}</div>}
        </Card>
      ))}
    </div>
  );
}
