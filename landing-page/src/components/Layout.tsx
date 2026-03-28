import { Outlet, useLocation } from "react-router";
import { useEffect } from "react";
import Nav from "./Nav";
import Footer from "./Footer";

export default function Layout() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="min-h-screen bg-[rgb(4,7,13)] text-[rgb(213,219,230)]">
      <Nav />
      <main>
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
