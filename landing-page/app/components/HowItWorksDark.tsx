import HowItWorksDesktop from "../../imports/HowItWorksDesktop";

export default function HowItWorksDark() {
  return (
    <div className="size-full bg-[#0a0a0b] overflow-auto">
      <div className="min-h-full dark-theme-wrapper">
        <style>{`
          .dark-theme-wrapper {
            /* Override all background colors */
            --fill-0: white;
            --stroke-0: white;
          }

          /* Header and navigation */
          .dark-theme-wrapper [data-name="Header"],
          .dark-theme-wrapper [data-name="Navbar"] {
            background: rgba(255, 255, 255, 0.03) !important;
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          }

          /* Hide the duplicate navigation bar from Figma import */
          .dark-theme-wrapper > div > div:first-child {
            display: none !important;
          }

          /* All white backgrounds become dark */
          .dark-theme-wrapper .bg-white {
            background: transparent !important;
          }

          /* Section containers should be fully transparent */
          .dark-theme-wrapper > div > div > div.bg-white {
            background: transparent !important;
          }

          /* Text colors */
          .dark-theme-wrapper .text-black,
          .dark-theme-wrapper [style*="text-black"],
          .dark-theme-wrapper p:not([class*="text-white"]):not([class*="text-gray"]) {
            color: white !important;
          }

          /* Headings use Inter Bold */
          .dark-theme-wrapper [class*="Roboto:Bold"],
          .dark-theme-wrapper [style*="font-['Roboto:Bold"] {
            font-family: 'Inter', sans-serif !important;
            font-weight: 800 !important;
          }

          /* Semi-bold becomes bold Inter */
          .dark-theme-wrapper [class*="Roboto:SemiBold"],
          .dark-theme-wrapper [style*="font-['Roboto:SemiBold"] {
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
          }

          /* Regular text uses Inter */
          .dark-theme-wrapper [class*="Roboto:Regular"],
          .dark-theme-wrapper [style*="font-['Roboto:Regular"] {
            font-family: 'Inter', sans-serif !important;
            font-weight: 400 !important;
          }

          /* Body text in gray */
          .dark-theme-wrapper [class*="Roboto:Regular"][style*="text-[18px]"],
          .dark-theme-wrapper [class*="Roboto:Regular"][style*="text-[14px]"] {
            color: #d1d5db !important;
          }

          /* Remove glassmorphic styling from broad containers - keep backgrounds black/transparent */
          .dark-theme-wrapper [data-name*="Layout"],
          .dark-theme-wrapper [data-name*="Section"] {
            background: transparent !important;
          }

          /* Only apply glassmorphic cards to specific feature/card elements, not sections */
          .dark-theme-wrapper [data-name*="Feature"][data-name*="Card"],
          .dark-theme-wrapper [data-name*="Card"]:not([data-name*="Section"]) {
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 24px !important;
          }

          /* Primary buttons */
          .dark-theme-wrapper .bg-black,
          .dark-theme-wrapper [data-name="Button"] .bg-black {
            background: #00ffc2 !important;
            border-color: #00ffc2 !important;
          }

          .dark-theme-wrapper .bg-black p,
          .dark-theme-wrapper .bg-black .text-white {
            color: #0a0a0b !important;
            font-weight: 600 !important;
          }

          /* Secondary buttons */
          .dark-theme-wrapper [data-name="Button"]:not(:has(.bg-black)) {
            border-color: #4b5563 !important;
            background: transparent !important;
          }

          .dark-theme-wrapper [data-name="Button"]:not(:has(.bg-black)):hover {
            border-color: #00ffc2 !important;
            background: rgba(0, 255, 194, 0.1) !important;
          }

          /* Border colors */
          .dark-theme-wrapper .border-black,
          .dark-theme-wrapper [aria-hidden="true"].border-black {
            border-color: #4b5563 !important;
          }

          /* SVG icons */
          .dark-theme-wrapper svg path[fill*="black"],
          .dark-theme-wrapper svg path[id*="Vector"] {
            fill: #00ffc2 !important;
          }

          .dark-theme-wrapper svg path[stroke*="black"] {
            stroke: #00ffc2 !important;
          }

          /* Menu items hover */
          .dark-theme-wrapper [data-name="Menu Item"]:hover {
            background: rgba(0, 255, 194, 0.05) !important;
            border-radius: 12px;
            cursor: pointer;
          }

          /* Tab styling */
          .dark-theme-wrapper [data-name*="Tab"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
          }

          .dark-theme-wrapper [data-name*="Tab"]:hover {
            background: rgba(0, 255, 194, 0.1) !important;
            border-color: #00ffc2 !important;
          }

          /* Links and interactive elements */
          .dark-theme-wrapper a,
          .dark-theme-wrapper [data-name*="Nav Link"] {
            color: #d1d5db !important;
            transition: color 0.2s;
          }

          .dark-theme-wrapper a:hover,
          .dark-theme-wrapper [data-name*="Nav Link"]:hover {
            color: #00ffc2 !important;
          }

          /* Taglines and labels */
          .dark-theme-wrapper [data-name*="Tagline"] p,
          .dark-theme-wrapper [data-name="Section Info"] p {
            color: #00ffc2 !important;
          }

          /* Images */
          .dark-theme-wrapper img {
            border-radius: 16px;
            opacity: 0.9;
          }

          /* Dropdown menus */
          .dark-theme-wrapper [data-name*="Menu List"] {
            background: rgba(10, 10, 11, 0.95) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 16px !important;
            padding: 16px;
          }

          /* Footer */
          .dark-theme-wrapper [data-name="Footer"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
          }

          /* CTA sections */
          .dark-theme-wrapper [data-name*="Cta"] {
            background: rgba(0, 255, 194, 0.05) !important;
            border: 1px solid rgba(0, 255, 194, 0.2) !important;
            border-radius: 24px !important;
          }

          /* Step indicators and numbers */
          .dark-theme-wrapper [data-name*="Number"],
          .dark-theme-wrapper [data-name*="Step"] {
            color: #00ffc2 !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
          }
        `}</style>
        <HowItWorksDesktop />
      </div>
    </div>
  );
}
