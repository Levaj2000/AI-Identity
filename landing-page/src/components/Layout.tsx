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
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-[rgb(166,218,255)] focus:text-[rgb(4,7,13)] focus:rounded-lg focus:font-medium focus:text-sm"
      >
        Skip to main content
      </a>
      <Nav />
      <main id="main-content">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
