import { Link, useLocation } from "react-router";
import { AIIdentityLogo5 } from "./AIIdentityLogo";
import { useState } from "react";
import { ChevronDown } from "lucide-react";

export default function Navigation() {
  const location = useLocation();
  const [isResourcesOpen, setIsResourcesOpen] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0a0a0b]/80 backdrop-blur-[20px] border-b border-white/10">
      <div className="max-w-[1280px] mx-auto px-[64px] h-[72px] flex items-center justify-between">
        <Link to="/" className="flex items-center">
          <AIIdentityLogo5 className="h-[32px] w-auto" variant="primary" />
        </Link>

        <div className="flex gap-[32px] items-center">
          <Link
            to="/"
            className={`font-['Inter',sans-serif] font-normal text-[16px] transition-colors ${
              isActive('/') ? 'text-[#00ffc2]' : 'text-gray-300 hover:text-white'
            }`}
          >
            Home
          </Link>
          <Link
            to="/how-it-works"
            className={`font-['Inter',sans-serif] font-normal text-[16px] transition-colors ${
              isActive('/how-it-works') ? 'text-[#00ffc2]' : 'text-gray-300 hover:text-white'
            }`}
          >
            How it works
          </Link>
          <Link
            to="/integrations"
            className={`font-['Inter',sans-serif] font-normal text-[16px] transition-colors ${
              isActive('/integrations') ? 'text-[#00ffc2]' : 'text-gray-300 hover:text-white'
            }`}
          >
            Integrations
          </Link>
          <Link
            to="/security"
            className={`font-['Inter',sans-serif] font-normal text-[16px] transition-colors ${
              isActive('/security') ? 'text-[#00ffc2]' : 'text-gray-300 hover:text-white'
            }`}
          >
            Security
          </Link>

          {/* Resources Dropdown */}
          <div
            className="relative"
            onMouseEnter={() => setIsResourcesOpen(true)}
            onMouseLeave={() => setIsResourcesOpen(false)}
          >
            <button className="flex items-center gap-1 font-['Inter',sans-serif] font-normal text-[16px] text-gray-300 hover:text-white transition-colors">
              Resources
              <ChevronDown className={`w-4 h-4 transition-transform ${isResourcesOpen ? 'rotate-180' : ''}`} />
            </button>

            {isResourcesOpen && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-4 pt-4 z-[100]">
                <div className="bg-[#0a0a0b]/95 backdrop-blur-[20px] border border-white/10 rounded-2xl p-8 shadow-2xl min-w-[900px]">
                  <div className="grid grid-cols-4 gap-8">
                    {/* Platform Column */}
                    <div className="flex flex-col gap-4">
                      <h3 className="font-['Inter',sans-serif] font-semibold text-[14px] text-[#00ffc2] uppercase tracking-wider">Platform</h3>
                      <Link to="/how-it-works" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Proxy gateway</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Secure authentication for autonomous agents</span>
                      </Link>
                      <a href="#docs" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">API reference</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Complete technical documentation and examples</span>
                      </a>
                      <Link to="/security" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Fail-closed security</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Deny-by-default when errors occur</span>
                      </Link>
                      <Link to="/integrations" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Framework support</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Native integration with leading AI platforms</span>
                      </Link>
                    </div>

                    {/* Developers Column */}
                    <div className="flex flex-col gap-4">
                      <h3 className="font-['Inter',sans-serif] font-semibold text-[14px] text-[#00ffc2] uppercase tracking-wider">Developers</h3>
                      <a href="#signup" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Get started</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Build your first identity in minutes</span>
                      </a>
                      <a href="#docs" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Documentation</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Explore our complete developer guides</span>
                      </a>
                      <a href="#docs" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Code samples</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Ready-to-use implementations for your stack</span>
                      </a>
                      <a href="#community" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Community</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Join developers building the future</span>
                      </a>
                    </div>

                    {/* Company Column */}
                    <div className="flex flex-col gap-4">
                      <h3 className="font-['Inter',sans-serif] font-semibold text-[14px] text-[#00ffc2] uppercase tracking-wider">Company</h3>
                      <a href="#about" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">About us</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Learn our mission and approach</span>
                      </a>
                      <a href="#blog" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Blog</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Insights on identity and AI security</span>
                      </a>
                      <a href="#contact" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Contact</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Reach out to our team directly</span>
                      </a>
                      <a href="#careers" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Careers</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Join us in securing autonomous systems</span>
                      </a>
                    </div>

                    {/* Legal Column */}
                    <div className="flex flex-col gap-4">
                      <h3 className="font-['Inter',sans-serif] font-semibold text-[14px] text-[#00ffc2] uppercase tracking-wider">Legal</h3>
                      <a href="#privacy" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Privacy</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">How we protect your data</span>
                      </a>
                      <a href="#terms" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Terms</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Our service terms and conditions</span>
                      </a>
                      <Link to="/security" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Security</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Our commitment to your protection</span>
                      </Link>
                      <a href="#compliance" className="group flex flex-col gap-1 py-2 hover:translate-x-1 transition-transform">
                        <span className="font-['Inter',sans-serif] font-medium text-[14px] text-white group-hover:text-[#00ffc2]">Compliance</span>
                        <span className="font-['Inter',sans-serif] font-normal text-[12px] text-gray-400">Standards we meet and exceed</span>
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>

        <div className="flex gap-[16px] items-center">
          <a href="#demo" className="px-[20px] py-[8px] border border-gray-600 rounded-lg font-['Inter',sans-serif] font-normal text-[16px] text-white hover:border-[#00ffc2] hover:bg-[#00ffc2]/10 transition-all">
            Demo
          </a>
          <a href="#signup" className="px-[20px] py-[8px] bg-[#00ffc2] rounded-lg font-['Inter',sans-serif] font-semibold text-[16px] text-[#0a0a0b] hover:bg-[#00e6ad] transition-colors">
            Start
          </a>
        </div>
      </div>
    </nav>
  );
}
