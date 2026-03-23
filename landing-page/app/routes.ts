import { createBrowserRouter } from "react-router";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import HowItWorks from "./pages/HowItWorks";
import Integrations from "./pages/Integrations";
import Security from "./pages/Security";
import Contact from "./pages/Contact";
import Privacy from "./pages/Privacy";
import Terms from "./pages/Terms";
import Blog from "./pages/Blog";
import Careers from "./pages/Careers";
import Docs from "./pages/Docs";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: Home },
      { path: "how-it-works", Component: HowItWorks },
      { path: "integrations", Component: Integrations },
      { path: "security", Component: Security },
      { path: "contact", Component: Contact },
      { path: "privacy", Component: Privacy },
      { path: "terms", Component: Terms },
      { path: "blog", Component: Blog },
      { path: "blog/:slug", Component: Blog },
      { path: "careers", Component: Careers },
      { path: "docs", Component: Docs },
    ],
  },
]);
