import { getInitData } from "./tg";

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "/api";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  headers.set("Content-Type", "application/json");
  const initData = getInitData();
  if (initData) headers.set("Authorization", `tma ${initData}`);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = "";
    try {
      const data = await res.json();
      detail = (data && (data.detail || data.message)) || "";
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

export const api = {
  me: () => request<MeOut>(`/me`),

  cities: () => request<CityOut[]>(`/cities`),
  cityProducts: (cityId: number) => request<ProductOut[]>(`/cities/${cityId}/products`),
  product: (id: number) => request<ProductOut>(`/products/${id}`),

  cart: () => request<CartOut>(`/cart`),
  cartAdd: (product_id: number, quantity = 1) =>
    request<CartOut>(`/cart/items`, { method: "POST", body: JSON.stringify({ product_id, quantity }) }),
  cartUpdate: (id: number, quantity: number) =>
    request<CartOut>(`/cart/items/${id}`, { method: "PATCH", body: JSON.stringify({ quantity }) }),
  cartRemove: (id: number) => request<CartOut>(`/cart/items/${id}`, { method: "DELETE" }),
  cartClear: () => request<CartOut>(`/cart`, { method: "DELETE" }),

  wallet: () => request<WalletOut>(`/wallet`),
  walletPayments: () => request<PaymentOut[]>(`/wallet/payments`),
  walletAddresses: () => request<{ TON: string; USDT_TRC20: string }>(`/wallet/crypto-addresses`),
  walletTopup: (amount_usdt: number, method: string) =>
    request<PaymentOut>(`/wallet/topup`, { method: "POST", body: JSON.stringify({ amount_usdt, method }) }),
  walletSubmitTx: (paymentId: number, txid: string) =>
    request<PaymentOut>(`/wallet/payments/${paymentId}/tx`, { method: "POST", body: JSON.stringify({ txid }) }),

  checkout: (body: CheckoutIn) =>
    request<CheckoutOut>(`/checkout`, { method: "POST", body: JSON.stringify(body) }),
  orders: () => request<OrderListItem[]>(`/orders`),
  order: (id: number) => request<OrderDetailOut>(`/orders/${id}`),
  confirmExternalPayment: (id: number) =>
    request<OrderDetailOut>(`/orders/${id}/confirm-payment`, { method: "POST" }),

  reviews: () => request<ReviewOut[]>(`/reviews`),
  reviewCreate: (order_id: number, rating: number, text: string) =>
    request<ReviewOut>(`/reviews`, { method: "POST", body: JSON.stringify({ order_id, rating, text }) }),

  disputes: () => request<DisputeOut[]>(`/disputes`),
  disputeOpen: (order_id: number, reason: string) =>
    request<DisputeOut>(`/disputes`, { method: "POST", body: JSON.stringify({ order_id, reason }) }),
  disputeTake: (id: number) =>
    request<{ ok: boolean }>(`/disputes/${id}/take`, { method: "POST" }),
  disputeResolve: (id: number, refund: boolean, note = "") =>
    request<{ ok: boolean }>(`/disputes/${id}/resolve`, { method: "POST", body: JSON.stringify({ refund, note }) }),
  disputeChat: (id: number) => request<ChatMessageOut[]>(`/disputes/${id}/chat`),
  disputeChatSend: (id: number, text?: string, photo_data_url?: string) =>
    request<ChatMessageOut>(`/disputes/${id}/chat`, { method: "POST", body: JSON.stringify({ text, photo_data_url }) }),

  chatHistory: (orderId: number) => request<ChatMessageOut[]>(`/orders/${orderId}/chat`),
  chatSend: (orderId: number, text?: string, photo_data_url?: string) =>
    request<ChatMessageOut>(`/orders/${orderId}/chat`, { method: "POST", body: JSON.stringify({ text, photo_data_url }) }),

  courierOrders: () => request<CourierOrder[]>(`/courier/orders`),
  courierTake: (id: number) =>
    request<{ ok: boolean }>(`/courier/orders/${id}/take`, { method: "POST" }),
  courierDeliver: (id: number) =>
    request<{ ok: boolean }>(`/courier/orders/${id}/deliver`, { method: "POST" }),

  // admin
  adminCities: () => request<AdminCity[]>(`/admin/cities`),
  adminCreateCity: (name: string, delivery_price_usdt: number) =>
    request<AdminCity>(`/admin/cities`, { method: "POST", body: JSON.stringify({ name, delivery_price_usdt }) }),
  adminUpdateCity: (id: number, body: Partial<AdminCity>) =>
    request<AdminCity>(`/admin/cities/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  adminDeleteCity: (id: number) =>
    request<{ ok: boolean }>(`/admin/cities/${id}`, { method: "DELETE" }),

  adminProducts: (cityId?: number) =>
    request<AdminProduct[]>(`/admin/products${cityId ? `?city_id=${cityId}` : ""}`),
  adminCreateProduct: (body: AdminProductCreate) =>
    request<{ id: number }>(`/admin/products`, { method: "POST", body: JSON.stringify(body) }),
  adminUpdateProduct: (id: number, body: Partial<AdminProductCreate & { is_active: boolean }>) =>
    request<{ ok: boolean }>(`/admin/products/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  adminDeleteProduct: (id: number) =>
    request<{ ok: boolean }>(`/admin/products/${id}`, { method: "DELETE" }),

  adminCouriers: () => request<AdminCourier[]>(`/admin/couriers`),
  adminAssignCourier: (user_id: number, city_id: number) =>
    request<{ ok: boolean }>(`/admin/couriers`, { method: "POST", body: JSON.stringify({ user_id, city_id }) }),
  adminRemoveCourier: (user_id: number) =>
    request<{ ok: boolean }>(`/admin/couriers/${user_id}`, { method: "DELETE" }),

  adminPayments: (status?: string) =>
    request<AdminPayment[]>(`/admin/payments${status ? `?status=${status}` : ""}`),
  adminApprovePayment: (id: number) =>
    request<PaymentOut>(`/admin/payments/${id}/approve`, { method: "POST", body: JSON.stringify({}) }),
  adminRejectPayment: (id: number, note = "") =>
    request<PaymentOut>(`/admin/payments/${id}/reject`, { method: "POST", body: JSON.stringify({ note }) }),

  adminFreeCredits: (user_id: number, amount: number) =>
    request<{ ok: boolean; free_credits: number }>(`/admin/free-credits`, { method: "POST", body: JSON.stringify({ user_id, amount }) }),
};

// ---------- types ----------

export type MeOut = {
  id: number;
  username: string | null;
  full_name: string | null;
  balance_usdt: number;
  free_credits: number;
  is_admin: boolean;
  is_moderator: boolean;
  courier_city_id: number | null;
};

export type CityOut = {
  id: number;
  name: string;
  delivery_price_usdt: number;
  is_active: boolean;
  products_count: number;
};

export type ProductOut = {
  id: number;
  city_id: number;
  city_name: string;
  name: string;
  description: string;
  photo_url: string | null;
  price_usdt: number;
  stock: number;
  is_active: boolean;
};

export type CartItemOut = {
  id: number;
  product_id: number;
  product_name: string;
  city_id: number;
  city_name: string;
  price_usdt: number;
  delivery_price_usdt: number;
  quantity: number;
  photo_url: string | null;
};

export type CartOut = {
  items: CartItemOut[];
  items_total_usdt: number;
  delivery_total_usdt: number;
  total_usdt: number;
};

export type WalletOut = { balance_usdt: number; free_credits: number };
export type PaymentOut = {
  id: number;
  kind: string;
  amount_usdt: number;
  method: string;
  status: string;
  txid: string | null;
  created_at: string;
  confirmed_at: string | null;
};

export type CheckoutIn = {
  method: string;
  addresses: { city_id: number; address: string }[];
};

export type CheckoutOut = {
  paid_from_balance: boolean;
  payment_id: number | null;
  order_ids: number[];
  crypto_wallet?: string | null;
  amount_usdt?: number | null;
  method: string;
};

export type OrderListItem = {
  id: number;
  status: string;
  product_name: string;
  city_name: string;
  total_usdt: number;
  created_at: string;
};

export type OrderDetailOut = {
  id: number;
  status: string;
  product_id: number;
  product_name: string;
  city_id: number;
  city_name: string;
  delivery_address: string | null;
  payment_method: string | null;
  product_price_usdt: number;
  delivery_price_usdt: number;
  total_usdt: number;
  is_free: boolean;
  courier_id: number | null;
  courier_name: string | null;
  created_at: string;
  paid_at: string | null;
  delivered_at: string | null;
};

export type ReviewOut = {
  id: number;
  user_name: string;
  rating: number;
  text: string;
  created_at: string;
};

export type DisputeOut = {
  id: number;
  order_id: number;
  status: string;
  reason: string;
  moderator_id: number | null;
  moderator_name: string | null;
  opened_at: string;
  closed_at: string | null;
};

export type ChatMessageOut = {
  id: number;
  sender_id: number;
  sender_name: string;
  kind: string;
  text: string | null;
  photo_url: string | null;
  created_at: string;
};

export type CourierOrder = {
  id: number;
  status: string;
  product_name: string;
  city_name: string;
  delivery_address: string;
  total_usdt: number;
  created_at: string;
  is_mine: boolean;
};

export type AdminCity = {
  id: number;
  name: string;
  delivery_price_usdt: number;
  is_active: boolean;
};

export type AdminProduct = {
  id: number;
  city_id: number;
  city_name: string;
  name: string;
  description: string;
  photo_url: string | null;
  price_usdt: number;
  stock: number;
  is_active: boolean;
};

export type AdminProductCreate = {
  city_id: number;
  name: string;
  description: string;
  price_usdt: number;
  stock: number;
  photo_url?: string | null;
};

export type AdminCourier = {
  user_id: number;
  username: string | null;
  full_name: string | null;
  city_id: number;
  city_name: string;
};

export type AdminPayment = {
  id: number;
  user_id: number;
  user_name: string;
  kind: string;
  amount_usdt: number;
  method: string;
  txid: string | null;
  status: string;
  created_at: string;
};
