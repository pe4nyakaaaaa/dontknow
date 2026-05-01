import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Pencil, Check, X } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Loading, ErrorBox, Empty } from "@/components/Loading";
import { PageHeader } from "@/components/Header";
import { fmt, fmtDate } from "@/lib/utils";
import { toast } from "sonner";

export default function Admin() {
  const meQ = useQuery({ queryKey: ["me"], queryFn: api.me });
  const [tab, setTab] = useState<"cities" | "products" | "couriers" | "payments">("cities");

  if (meQ.isLoading) return <Loading />;
  if (!meQ.data?.is_admin) return <ErrorBox error="Доступ запрещён" />;

  return (
    <div className="space-y-4">
      <PageHeader title="Админ-панель" subtitle="Города, товары, курьеры, платежи" />
      <div className="grid grid-cols-4 gap-2 text-xs">
        {[
          ["cities", "🏙 Города"],
          ["products", "🛍 Товары"],
          ["couriers", "🚴 Курьеры"],
          ["payments", "🧾 Платежи"],
        ].map(([k, l]) => (
          <button
            key={k}
            onClick={() => setTab(k as typeof tab)}
            className={`rounded-xl py-2 border ${tab === k ? "border-neon bg-neon/15 text-neon-soft shadow-neon" : "border-border bg-background/40 hover:border-neon/40"}`}
          >
            {l}
          </button>
        ))}
      </div>
      {tab === "cities" && <CitiesTab />}
      {tab === "products" && <ProductsTab />}
      {tab === "couriers" && <CouriersTab />}
      {tab === "payments" && <PaymentsTab />}
    </div>
  );
}

function CitiesTab() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-cities"], queryFn: api.adminCities });
  const [name, setName] = useState("");
  const [price, setPrice] = useState("0");
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editPrice, setEditPrice] = useState("0");

  const createMut = useMutation({
    mutationFn: () => api.adminCreateCity(name.trim(), parseFloat(price) || 0),
    onSuccess: () => {
      setName(""); setPrice("0");
      qc.invalidateQueries({ queryKey: ["admin-cities"] });
      qc.invalidateQueries({ queryKey: ["cities"] });
      toast.success("Город добавлен");
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const updateMut = useMutation({
    mutationFn: () => api.adminUpdateCity(editId!, { name: editName.trim(), delivery_price_usdt: parseFloat(editPrice) || 0 }),
    onSuccess: () => {
      setEditId(null);
      qc.invalidateQueries({ queryKey: ["admin-cities"] });
      qc.invalidateQueries({ queryKey: ["cities"] });
      toast.success("Сохранено");
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => api.adminDeleteCity(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-cities"] });
      toast.success("Удалено");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-3">
      <Card className="space-y-2">
        <div className="font-semibold">➕ Новый город</div>
        <Input placeholder="Название" value={name} onChange={(e) => setName(e.target.value)} />
        <Input type="number" inputMode="decimal" placeholder="Стоимость доставки USDT" value={price} onChange={(e) => setPrice(e.target.value)} />
        <Button className="w-full" disabled={!name.trim() || createMut.isPending} onClick={() => createMut.mutate()}>
          <Plus className="w-4 h-4" /> Добавить
        </Button>
      </Card>
      {q.isLoading ? <Loading /> : !q.data?.length ? <Empty title="Нет городов" /> : (
        <div className="space-y-2">
          {q.data.map((c) => (
            <Card key={c.id} className="space-y-2">
              {editId === c.id ? (
                <>
                  <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
                  <Input type="number" inputMode="decimal" value={editPrice} onChange={(e) => setEditPrice(e.target.value)} />
                  <div className="grid grid-cols-2 gap-2">
                    <Button variant="secondary" onClick={() => setEditId(null)}><X className="w-4 h-4" /> Отмена</Button>
                    <Button onClick={() => updateMut.mutate()}><Check className="w-4 h-4" /> Сохранить</Button>
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold">🏙 {c.name}</div>
                    <div className="text-xs text-muted-foreground">Доставка: {fmt(c.delivery_price_usdt)} USDT · {c.is_active ? "активен" : "неактивен"}</div>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="secondary" size="icon" onClick={() => { setEditId(c.id); setEditName(c.name); setEditPrice(String(c.delivery_price_usdt)); }}>
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button variant="danger" size="icon" onClick={() => confirm("Удалить?") && deleteMut.mutate(c.id)}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function ProductsTab() {
  const qc = useQueryClient();
  const citiesQ = useQuery({ queryKey: ["admin-cities"], queryFn: api.adminCities });
  const productsQ = useQuery({ queryKey: ["admin-products"], queryFn: () => api.adminProducts() });
  const [form, setForm] = useState({ city_id: 0, name: "", description: "", price_usdt: "0", stock: "-1", photo_url: "" });

  const create = useMutation({
    mutationFn: () => api.adminCreateProduct({
      city_id: Number(form.city_id),
      name: form.name.trim(),
      description: form.description.trim(),
      price_usdt: parseFloat(form.price_usdt) || 0,
      stock: parseInt(form.stock || "-1", 10),
      photo_url: form.photo_url.trim() || null,
    }),
    onSuccess: () => {
      setForm({ city_id: 0, name: "", description: "", price_usdt: "0", stock: "-1", photo_url: "" });
      qc.invalidateQueries({ queryKey: ["admin-products"] });
      toast.success("Товар добавлен");
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const del = useMutation({
    mutationFn: (id: number) => api.adminDeleteProduct(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-products"] }),
  });

  return (
    <div className="space-y-3">
      <Card className="space-y-2">
        <div className="font-semibold">➕ Новый товар</div>
        <select
          value={form.city_id || ""}
          onChange={(e) => setForm({ ...form, city_id: Number(e.target.value) })}
          className="w-full h-11 rounded-xl bg-input border border-border px-3 text-sm"
        >
          <option value="">Выберите город</option>
          {citiesQ.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <Input placeholder="Название" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <Textarea placeholder="Описание" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <div className="grid grid-cols-2 gap-2">
          <Input type="number" inputMode="decimal" placeholder="Цена USDT" value={form.price_usdt} onChange={(e) => setForm({ ...form, price_usdt: e.target.value })} />
          <Input type="number" placeholder="Остаток (-1 = ∞)" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} />
        </div>
        <Input placeholder="URL фото (https://...)" value={form.photo_url} onChange={(e) => setForm({ ...form, photo_url: e.target.value })} />
        <Button className="w-full" disabled={!form.city_id || !form.name.trim() || create.isPending} onClick={() => create.mutate()}>
          <Plus className="w-4 h-4" /> Добавить
        </Button>
      </Card>
      {productsQ.isLoading ? <Loading /> : !productsQ.data?.length ? <Empty title="Товаров нет" /> : (
        <div className="space-y-2">
          {productsQ.data.map((p) => (
            <Card key={p.id} className="flex items-center gap-3">
              {p.photo_url ? (
                <img src={p.photo_url} alt="" className="w-14 h-14 rounded-xl object-cover" />
              ) : (
                <div className="w-14 h-14 rounded-xl bg-neon/15 border border-neon/30 flex items-center justify-center text-2xl">📦</div>
              )}
              <div className="flex-1 min-w-0">
                <div className="font-semibold truncate">{p.name}</div>
                <div className="text-xs text-muted-foreground">🏙 {p.city_name} · {fmt(p.price_usdt)} USDT · {p.stock < 0 ? "∞" : p.stock}</div>
              </div>
              <Button variant="danger" size="icon" onClick={() => confirm("Удалить?") && del.mutate(p.id)}>
                <Trash2 className="w-4 h-4" />
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function CouriersTab() {
  const qc = useQueryClient();
  const couriersQ = useQuery({ queryKey: ["admin-couriers"], queryFn: api.adminCouriers });
  const citiesQ = useQuery({ queryKey: ["admin-cities"], queryFn: api.adminCities });
  const [userId, setUserId] = useState("");
  const [cityId, setCityId] = useState("");

  const assign = useMutation({
    mutationFn: () => api.adminAssignCourier(Number(userId), Number(cityId)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-couriers"] });
      setUserId(""); setCityId("");
      toast.success("Курьер назначен");
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.adminRemoveCourier(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-couriers"] }),
  });

  return (
    <div className="space-y-3">
      <Card className="space-y-2">
        <div className="font-semibold">🚴 Назначить курьера</div>
        <div className="text-xs text-muted-foreground">Telegram ID пользователя (он должен сначала /start у бота)</div>
        <Input placeholder="user_id" value={userId} onChange={(e) => setUserId(e.target.value)} />
        <select value={cityId} onChange={(e) => setCityId(e.target.value)} className="w-full h-11 rounded-xl bg-input border border-border px-3 text-sm">
          <option value="">Город</option>
          {citiesQ.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <Button className="w-full" disabled={!userId || !cityId || assign.isPending} onClick={() => assign.mutate()}>
          <Plus className="w-4 h-4" /> Назначить
        </Button>
      </Card>
      {couriersQ.isLoading ? <Loading /> : !couriersQ.data?.length ? <Empty title="Курьеров нет" /> : (
        <div className="space-y-2">
          {couriersQ.data.map((c) => (
            <Card key={c.user_id} className="flex items-center justify-between">
              <div>
                <div className="font-semibold">{c.full_name || c.username || `id${c.user_id}`}</div>
                <div className="text-xs text-muted-foreground">id {c.user_id} · 🏙 {c.city_name}</div>
              </div>
              <Button variant="danger" size="icon" onClick={() => confirm("Снять?") && remove.mutate(c.user_id)}>
                <Trash2 className="w-4 h-4" />
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function PaymentsTab() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-payments"], queryFn: () => api.adminPayments(), refetchInterval: 8000 });

  const approve = useMutation({
    mutationFn: (id: number) => api.adminApprovePayment(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-payments"] });
      toast.success("Подтверждено");
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const reject = useMutation({
    mutationFn: (id: number) => api.adminRejectPayment(id, "отклонено админом"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-payments"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (q.isLoading) return <Loading />;
  if (!q.data?.length) return <Empty title="Нет платежей на проверке" icon="✅" />;

  return (
    <div className="space-y-3">
      {q.data.map((p) => (
        <Card key={p.id} className="space-y-1">
          <div className="flex items-center justify-between">
            <div className="font-semibold">#{p.id} · {p.user_name}</div>
            <div className="text-neon-soft font-bold">{fmt(p.amount_usdt)} USDT</div>
          </div>
          <div className="text-xs text-muted-foreground">
            {p.kind} · {p.method} · {fmtDate(p.created_at)}
          </div>
          {p.txid && (
            <div className="text-[11px] font-mono break-all rounded-lg bg-input border border-border p-2">
              {p.txid}
            </div>
          )}
          <div className="grid grid-cols-2 gap-2 mt-1">
            <Button variant="secondary" onClick={() => reject.mutate(p.id)}>Отклонить</Button>
            <Button variant="success" onClick={() => approve.mutate(p.id)}>Подтвердить</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}
