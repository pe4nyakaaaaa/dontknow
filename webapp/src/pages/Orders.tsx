import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Send, Image as ImageIcon } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Loading, ErrorBox, Empty } from "@/components/Loading";
import { PageHeader } from "@/components/Header";
import { fmt, fmtDate } from "@/lib/utils";
import { haptic } from "@/lib/tg";
import { toast } from "sonner";

const STATUS_LABEL: Record<string, string> = {
  AWAITING_PAYMENT: "ожидает оплаты",
  PAID: "оплачен",
  IN_DELIVERY: "в доставке",
  DELIVERED: "доставлен",
  CANCELED: "отменён",
  REFUNDED: "возмещён",
  DISPUTED: "диспут",
};

const STATUS_COLOR: Record<string, string> = {
  AWAITING_PAYMENT: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  PAID: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  IN_DELIVERY: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  DELIVERED: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  CANCELED: "bg-destructive/15 text-destructive-foreground border-destructive/30",
  REFUNDED: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  DISPUTED: "bg-violet-500/15 text-violet-300 border-violet-500/30",
};

function StatusPill({ status }: { status: string }) {
  return (
    <span className={`inline-block text-[10px] rounded-full border px-2 py-0.5 ${STATUS_COLOR[status] ?? ""}`}>
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

export function OrdersList() {
  const { data, isLoading, error } = useQuery({ queryKey: ["orders"], queryFn: api.orders });
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data?.length) return <Empty title="Заказов пока нет" hint="После покупки они появятся здесь" icon="📜" />;
  return (
    <div className="space-y-3">
      <PageHeader title="Мои заказы" />
      {data.map((o) => (
        <Link key={o.id} to={`/orders/${o.id}`}>
          <Card className="flex items-center justify-between gap-3 hover:border-neon/60 transition-colors">
            <div>
              <div className="font-semibold">#{o.id} · {o.product_name}</div>
              <div className="text-xs text-muted-foreground">🏙 {o.city_name} · {fmtDate(o.created_at)}</div>
            </div>
            <div className="text-right space-y-1">
              <div className="font-bold text-neon-soft">{fmt(o.total_usdt)} USDT</div>
              <StatusPill status={o.status} />
            </div>
          </Card>
        </Link>
      ))}
    </div>
  );
}

export function OrderDetail() {
  const { id } = useParams();
  const oid = Number(id);
  const qc = useQueryClient();
  const orderQ = useQuery({
    queryKey: ["order", oid],
    queryFn: () => api.order(oid),
    refetchInterval: 6000,
    enabled: Number.isFinite(oid),
  });
  const meQ = useQuery({ queryKey: ["me"], queryFn: api.me });

  const [reviewOpen, setReviewOpen] = useState(false);
  const [rating, setRating] = useState(5);
  const [reviewText, setReviewText] = useState("");

  const reviewMut = useMutation({
    mutationFn: () => api.reviewCreate(oid, rating, reviewText),
    onSuccess: () => {
      toast.success("Спасибо за отзыв!");
      setReviewOpen(false);
      setReviewText("");
      qc.invalidateQueries({ queryKey: ["reviews"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const [disputeOpen, setDisputeOpen] = useState(false);
  const [reason, setReason] = useState("");
  const disputeMut = useMutation({
    mutationFn: () => api.disputeOpen(oid, reason),
    onSuccess: (d) => {
      toast.success("Диспут открыт");
      setDisputeOpen(false);
      setReason("");
      qc.invalidateQueries({ queryKey: ["order", oid] });
      window.location.hash = `#/disputes/${d.id}`;
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (orderQ.isLoading) return <Loading />;
  if (orderQ.error || !orderQ.data) return <ErrorBox error={orderQ.error} />;
  const o = orderQ.data;
  const showChat = o.courier_id != null;

  return (
    <div className="space-y-4">
      <PageHeader title={`Заказ #${o.id}`} right={<StatusPill status={o.status} />} />
      <Card className="space-y-2 text-sm">
        <Row label="Товар" value={o.product_name} />
        <Row label="Город" value={o.city_name} />
        {o.delivery_address && <Row label="Адрес" value={o.delivery_address} />}
        {o.courier_name && <Row label="Курьер" value={o.courier_name} />}
        <div className="border-t border-border my-2" />
        <Row label="Цена товара" value={`${fmt(o.product_price_usdt)} USDT`} />
        <Row label="Доставка" value={`${fmt(o.delivery_price_usdt)} USDT`} />
        <Row label="Итого" value={`${fmt(o.total_usdt)} USDT`} bold />
        {o.payment_method && <Row label="Оплата" value={o.payment_method} />}
        <Row label="Создан" value={fmtDate(o.created_at)} />
        {o.delivered_at && <Row label="Доставлен" value={fmtDate(o.delivered_at)} />}
      </Card>

      {o.status === "AWAITING_PAYMENT" && o.payment_method && o.payment_method !== "BALANCE" && (
        <Card className="space-y-2">
          <div className="text-sm">Переведите крипту и подтвердите оплату — админ увидит заявку.</div>
          <Button
            className="w-full"
            onClick={async () => {
              try {
                await api.confirmExternalPayment(oid);
                qc.invalidateQueries({ queryKey: ["order", oid] });
                toast.success("Заявка отправлена");
              } catch (e) {
                toast.error((e as Error).message);
              }
            }}
          >
            Я оплатил — отправить на проверку
          </Button>
        </Card>
      )}

      {showChat && o.status !== "AWAITING_PAYMENT" && (
        <ChatBox
          orderId={oid}
          isCourier={meQ.data?.id === o.courier_id}
        />
      )}

      {o.status === "DELIVERED" && (
        <>
          {!reviewOpen ? (
            <Button variant="secondary" className="w-full" onClick={() => setReviewOpen(true)}>
              ✍️ Оставить отзыв
            </Button>
          ) : (
            <Card className="space-y-3">
              <StarPicker value={rating} onChange={setRating} />
              <Textarea placeholder="Расскажите о покупке..." value={reviewText} onChange={(e) => setReviewText(e.target.value)} />
              <div className="grid grid-cols-2 gap-2">
                <Button variant="secondary" onClick={() => setReviewOpen(false)}>Отмена</Button>
                <Button disabled={reviewMut.isPending} onClick={() => reviewMut.mutate()}>Отправить</Button>
              </div>
            </Card>
          )}
        </>
      )}

      {o.status !== "DISPUTED" && o.status !== "CANCELED" && (
        <>
          {!disputeOpen ? (
            <Button variant="ghost" className="w-full" onClick={() => setDisputeOpen(true)}>
              ⚖️ Открыть диспут
            </Button>
          ) : (
            <Card className="space-y-3">
              <Textarea placeholder="Опишите проблему" value={reason} onChange={(e) => setReason(e.target.value)} />
              <div className="grid grid-cols-2 gap-2">
                <Button variant="secondary" onClick={() => setDisputeOpen(false)}>Отмена</Button>
                <Button variant="danger" disabled={!reason.trim() || disputeMut.isPending} onClick={() => disputeMut.mutate()}>
                  Открыть диспут
                </Button>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className={bold ? "font-bold text-neon-soft text-base" : "text-right"}>{value}</div>
    </div>
  );
}

function StarPicker({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex justify-center gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={`text-3xl transition-transform ${n <= value ? "text-neon-soft drop-shadow-[0_0_10px_rgba(168,85,247,0.7)]" : "text-muted-foreground"}`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

function ChatBox({ orderId, isCourier }: { orderId: number; isCourier: boolean }) {
  const qc = useQueryClient();
  const meQ = useQuery({ queryKey: ["me"], queryFn: api.me });
  const messagesQ = useQuery({
    queryKey: ["chat", orderId],
    queryFn: () => api.chatHistory(orderId),
    refetchInterval: 4000,
  });
  const [text, setText] = useState("");
  const [photo, setPhoto] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messagesQ.data?.length]);

  const sendMut = useMutation({
    mutationFn: () => api.chatSend(orderId, text || undefined, photo || undefined),
    onSuccess: () => {
      setText("");
      setPhoto(null);
      qc.invalidateQueries({ queryKey: ["chat", orderId] });
      haptic("ok");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deliverMut = useMutation({
    mutationFn: () => api.courierDeliver(orderId),
    onSuccess: () => {
      toast.success("Доставлено");
      qc.invalidateQueries({ queryKey: ["order", orderId] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const onFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => setPhoto(reader.result as string);
    reader.readAsDataURL(file);
  };

  return (
    <Card className="space-y-3">
      <div className="text-sm font-semibold">💬 Чат с {isCourier ? "покупателем" : "курьером"}</div>
      <div className="max-h-72 overflow-y-auto space-y-2 bg-input/40 rounded-xl p-2">
        {!messagesQ.data?.length && <div className="text-xs text-muted-foreground text-center py-6">Сообщений нет</div>}
        {messagesQ.data?.map((m) => {
          const mine = m.sender_id === meQ.data?.id;
          return (
            <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${mine ? "bg-neon-grad text-white" : "bg-card border border-border"}`}>
                {!mine && <div className="text-[10px] opacity-70 mb-1">{m.sender_name}</div>}
                {m.photo_url && <img src={m.photo_url} alt="" className="rounded-lg mb-1 max-h-48" />}
                {m.text && <div className="whitespace-pre-wrap">{m.text}</div>}
                <div className="text-[10px] opacity-60 mt-0.5">{fmtDate(m.created_at)}</div>
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
        <Input placeholder="Сообщение..." value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !sendMut.isPending && (text || photo)) sendMut.mutate(); }} />
        <Button size="icon" disabled={sendMut.isPending || (!text && !photo)} onClick={() => sendMut.mutate()}>
          <Send className="w-4 h-4" />
        </Button>
      </div>

      {isCourier && (
        <Button variant="success" className="w-full" disabled={deliverMut.isPending} onClick={() => deliverMut.mutate()}>
          📦 Отметить доставленным
        </Button>
      )}
    </Card>
  );
}
