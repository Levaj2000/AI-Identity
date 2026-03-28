import { createBrowserRouter, RouterProvider } from "react-router";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import HowItWorks from "./pages/HowItWorks";
import Security from "./pages/Security";
import Integrations from "./pages/Integrations";
import Architecture from "./pages/Architecture";
import Contact from "./pages/Contact";
import Blog from "./pages/Blog";
import BlogPost from "./pages/BlogPost";
import Docs from "./pages/Docs";
import EUAIActChecklist from "./pages/EUAIActChecklist";
import Privacy from "./pages/Privacy";
import Terms from "./pages/Terms";
import Careers from "./pages/Careers";
import Pricing from "./pages/Pricing";

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/how-it-works", element: <HowItWorks /> },
      { path: "/security", element: <Security /> },
      { path: "/integrations", element: <Integrations /> },
      { path: "/architecture", element: <Architecture /> },
      { path: "/pricing", element: <Pricing /> },
      { path: "/contact", element: <Contact /> },
      { path: "/blog", element: <Blog /> },
      { path: "/blog/:slug", element: <BlogPost /> },
      { path: "/docs", element: <Docs /> },
      { path: "/eu-ai-act-checklist", element: <EUAIActChecklist /> },
      { path: "/privacy", element: <Privacy /> },
      { path: "/terms", element: <Terms /> },
      { path: "/careers", element: <Careers /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
