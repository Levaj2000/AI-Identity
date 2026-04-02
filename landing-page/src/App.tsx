import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";
import Layout from "./components/Layout";

// Eagerly load the homepage — it's the most common entry point
import Home from "./pages/Home";

// Lazy-load all other pages for route-based code splitting
const HowItWorks = lazy(() => import("./pages/HowItWorks"));
const Security = lazy(() => import("./pages/Security"));
const Integrations = lazy(() => import("./pages/Integrations"));
const Architecture = lazy(() => import("./pages/Architecture"));
const Contact = lazy(() => import("./pages/Contact"));
const Blog = lazy(() => import("./pages/Blog"));
const BlogPost = lazy(() => import("./pages/BlogPost"));
const Docs = lazy(() => import("./pages/Docs"));
const EUAIActChecklist = lazy(() => import("./pages/EUAIActChecklist"));
const Privacy = lazy(() => import("./pages/Privacy"));
const Terms = lazy(() => import("./pages/Terms"));
const Careers = lazy(() => import("./pages/Careers"));
const Pricing = lazy(() => import("./pages/Pricing"));
const UseCaseCustomerSupport = lazy(() => import("./pages/UseCaseCustomerSupport"));
const UseCaseCodingAssistant = lazy(() => import("./pages/UseCaseCodingAssistant"));
const UseCaseFinancialAgent = lazy(() => import("./pages/UseCaseFinancialAgent"));

function PageFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-6 h-6 border-2 border-[rgb(166,218,255)] border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function lazySuspense(Component: React.LazyExoticComponent<React.ComponentType>) {
  return (
    <Suspense fallback={<PageFallback />}>
      <Component />
    </Suspense>
  );
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/how-it-works", element: lazySuspense(HowItWorks) },
      { path: "/security", element: lazySuspense(Security) },
      { path: "/integrations", element: lazySuspense(Integrations) },
      { path: "/architecture", element: lazySuspense(Architecture) },
      { path: "/pricing", element: lazySuspense(Pricing) },
      { path: "/contact", element: lazySuspense(Contact) },
      { path: "/blog", element: lazySuspense(Blog) },
      { path: "/blog/:slug", element: lazySuspense(BlogPost) },
      { path: "/docs", element: lazySuspense(Docs) },
      { path: "/eu-ai-act-checklist", element: lazySuspense(EUAIActChecklist) },
      { path: "/use-cases/customer-support", element: lazySuspense(UseCaseCustomerSupport) },
      { path: "/use-cases/coding-assistant", element: lazySuspense(UseCaseCodingAssistant) },
      { path: "/use-cases/financial-compliance", element: lazySuspense(UseCaseFinancialAgent) },
      { path: "/privacy", element: lazySuspense(Privacy) },
      { path: "/terms", element: lazySuspense(Terms) },
      { path: "/careers", element: lazySuspense(Careers) },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
