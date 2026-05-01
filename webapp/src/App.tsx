import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { useEffect } from "react";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import { CatalogCities, CatalogProducts } from "@/pages/Catalog";
import Product from "@/pages/Product";
import Cart from "@/pages/Cart";
import Checkout from "@/pages/Checkout";
import Wallet from "@/pages/Wallet";
import { OrdersList, OrderDetail } from "@/pages/Orders";
import Reviews from "@/pages/Reviews";
import Admin from "@/pages/Admin";
import Courier from "@/pages/Courier";
import { ModeratorList, ModeratorDispute } from "@/pages/Moderator";
import { initTelegram } from "@/lib/tg";

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

export default function App() {
  useEffect(() => initTelegram(), []);
  return (
    <QueryClientProvider client={qc}>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/catalog" element={<CatalogCities />} />
            <Route path="/catalog/:cityId" element={<CatalogProducts />} />
            <Route path="/product/:id" element={<Product />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/wallet" element={<Wallet />} />
            <Route path="/orders" element={<OrdersList />} />
            <Route path="/orders/:id" element={<OrderDetail />} />
            <Route path="/reviews" element={<Reviews />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/courier" element={<Courier />} />
            <Route path="/moderator" element={<ModeratorList />} />
            <Route path="/disputes/:id" element={<ModeratorDispute />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </HashRouter>
      <Toaster position="top-center" theme="dark" richColors closeButton />
    </QueryClientProvider>
  );
}
