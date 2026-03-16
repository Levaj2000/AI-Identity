import { useState, useEffect } from "react";
import IntegrationsDark from "../components/IntegrationsDark";
import IntegrationsMobileDark from "../components/IntegrationsMobileDark";

export default function Integrations() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Check initial screen size
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);

    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);

  return isMobile ? <IntegrationsMobileDark /> : <IntegrationsDark />;
}
