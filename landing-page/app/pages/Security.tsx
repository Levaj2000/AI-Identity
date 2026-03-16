import { useState, useEffect } from "react";
import SecurityDark from "../components/SecurityDark";
import SecurityMobileDark from "../components/SecurityMobileDark";

export default function Security() {
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

  // Show desktop version for now until mobile is ready
  return isMobile ? <SecurityMobileDark /> : <SecurityDark />;
}
