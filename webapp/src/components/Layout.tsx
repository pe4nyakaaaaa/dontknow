import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Home, ShoppingCart, Wallet, Package, Star, Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEffect } from "react";
import { tg } from "@/lib/tg";

const NAV = [
  { to: "/", icon: Home, label: "Главная" },
  { to: "/catalog", icon: Menu, label: "Каталог" },
  { to: "/cart", icon: ShoppingCart, label: "Корзина" },
  { to: "/wallet", icon: Wallet, label: "Кошелёк" },
  { to: "/orders", icon: Package, label: "Заказы" },
  { to: "/reviews", icon: Star, label: "Отзывы" },
];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!tg?.BackButton) return;
    const showBack = location.pathname !== "/";
    if (showBack) tg.BackButton.show();
    else tg.BackButton.hide();
    const onClick = () => navigate(-1);
    tg.BackButton.onClick(onClick);
    return () => tg.BackButton?.offClick(onClick);
  }, [location.pathname, navigate]);

  return (
    <div className="min-h-screen flex flex-col">
      <main className="flex-1 px-4 pt-4 pb-28 max-w-2xl mx-auto w-full">
        <Outlet />
      </main>
      <nav className="fixed bottom-0 left-0 right-0 z-30 backdrop-blur-xl bg-background/80 border-t border-neon/15 pb-[max(env(safe-area-inset-bottom),8px)]">
        <div className="max-w-2xl mx-auto grid grid-cols-6 px-2 pt-2">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex flex-col items-center justify-center gap-1 py-1.5 rounded-xl text-[10px]",
                  isActive
                    ? "text-neon-soft"
                    : "text-muted-foreground hover:text-foreground",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <n.icon className={cn("w-5 h-5", isActive && "drop-shadow-[0_0_8px_rgba(168,85,247,0.7)]")} />
                  <span>{n.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
