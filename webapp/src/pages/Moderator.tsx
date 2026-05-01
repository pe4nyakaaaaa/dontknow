import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send, Image as ImageIcon } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Loading, ErrorBox, Empty } from "@/components/Loading";
import { PageHeader } from "@/components/Header";
import { fmtDate } from "@/lib/utils";
import { toast } from "sonner";

export function ModeratorList() {
  const q = useQuery({ queryKey: ["disputes"], queryFn: api.disputes, refetchInterval: 8000 });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  if (!q.data?.length) return <Empty title="Диспутов нет" icon="⚖️" />;
  return (
    <div className="space-y-3">
      <PageHeader title="Диспуты" subtitle="Открытые и закрытые" />
      {q.data.map((d) => (
        <Link key={d.id} to={`/disputes/${d.id}`}>
          <Card className="space-y-1 hover:border-neon/60 transition-colors">
            <div className="flex items-center justify-between">
              <div className="font-semibold">#{d.id} · заказ #{d.order_id}</div>
              <span className="text-[10px] rounded-full border border-neon/40 bg-neon/15 text-neon-soft px-2 py-0.5">{d.status}</span>
            </div>
            <div className="text-xs text-muted-foreground">{fmtDate(d.opened_at)}</div>
            {d.reason && <div className="text-sm">{d.reason}</div>}
          </Card>
        </Link>
      ))}
    </div>
  );
}

export function ModeratorDispute() {
  const { id } = useParams();
  const did = Number(id);
  const qc = useQueryClient();
  const meQ = useQuery({ queryKey: ["me"], queryFn: api.me });
  const list = useQuery({ queryKey: ["disputes"], queryFn: api.disputes });
  const dispute = list.data?.find((x) => x.id === did);
  const chatQ = useQuery({
    queryKey: ["dispute-chat", did],
    queryFn: () => api.disputeChat(did),
    refetchInterval: 4000,
    enabled: Number.isFinite(did),
  });

  const [text, setText] = useState("");
  const [photo, setPhoto] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [chatQ.data?.length]);

  const sendMut = useMutation({
    mutationFn: () => api.disputeChatSend(did, text || undefined, photo || undefined),
    onSuccess: () => {
      setText(""); setPhoto(null);
      qc.invalidateQueries({ queryKey: ["dispute-chat", did] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const takeMut = useMutation({
    mutationFn: () => api.disputeTake(did),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["disputes"] }),
    onError: (e: Error) => toast.error(e.message),
  });
  const resolveMut = useMutation({
    mutationFn: (refund: boolean) => api.disputeResolve(did, refund, note),
    onSuccess: () => {
      toast.success("Решение принято");
      qc.invalidateQueries({ queryKey: ["disputes"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const onFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => setPhoto(reader.result as string);
    reader.readAsDataURL(file);
  };

  if (list.isLoading) return <Loading />;
  if (!dispute) return <ErrorBox error="Диспут не найден" />;

  const isMod = meQ.data?.is_moderator;
  const isOpen = dispute.status === "OPEN";

  return (
    <div className="space-y-4">
      <PageHeader title={`Диспут #${dispute.id}`} subtitle={`Заказ #${dispute.order_id}`} right={<span className="text-[11px] rounded-full border px-2 py-0.5 bg-neon/15 text-neon-soft border-neon/40">{dispute.status}</span>} />
      <Card>
        <div className="text-xs text-muted-foreground mb-1">Причина:</div>
        <div className="text-sm whitespace-pre-wrap">{dispute.reason}</div>
      </Card>

      <Card className="space-y-3">
        <div className="text-sm font-semibold">💬 Диалог</div>
        <div className="max-h-72 overflow-y-auto space-y-2 bg-input/40 rounded-xl p-2">
          {!chatQ.data?.length && <div className="text-xs text-muted-foreground text-center py-6">Пока пусто</div>}
          {chatQ.data?.map((m) => {
            const mine = m.sender_id === meQ.data?.id;
            return (
              <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${mine ? "bg-neon-grad text-white" : "bg-card border border-border"}`}>
                  {!mine && <div className="text-[10px] opacity-70 mb-1">{m.sender_name}</div>}
                  {m.photo_url && <img src={m.photo_url} alt="" className="rounded-lg mb-1 max-h-48" />}
                  {m.text && <div className="whitespace-pre-wrap">{m.text}</div>}
                </div>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
        {photo && (
          <div className="relative">
            <img src={photo} alt="" className="rounded-lg max-h-32" />
            <button onClick={() => setPhoto(null)} className="absolute top-1 right-1 bg-background/80 rounded-full px-2 text-xs">×</button>
          </div>
        )}
        <div className="flex items-center gap-2">
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
          <Button variant="secondary" size="icon" onClick={() => fileRef.current?.click()}>
            <ImageIcon className="w-4 h-4" />
          </Button>
          <Input placeholder="Сообщение..." value={text} onChange={(e) => setText(e.target.value)} />
          <Button size="icon" disabled={sendMut.isPending || (!text && !photo)} onClick={() => sendMut.mutate()}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </Card>

      {isMod && isOpen && (
        <Card className="space-y-2">
          <div className="text-sm font-semibold">⚖️ Решение модератора</div>
          {!dispute.moderator_id && <Button variant="secondary" className="w-full" onClick={() => takeMut.mutate()}>Взять диспут</Button>}
          <Textarea placeholder="Резолюция / комментарий" value={note} onChange={(e) => setNote(e.target.value)} />
          <div className="grid grid-cols-2 gap-2">
            <Button variant="danger" disabled={resolveMut.isPending} onClick={() => resolveMut.mutate(false)}>Отказать</Button>
            <Button variant="success" disabled={resolveMut.isPending} onClick={() => resolveMut.mutate(true)}>Дать бесплатный заказ</Button>
          </div>
        </Card>
      )}
    </div>
  );
}
