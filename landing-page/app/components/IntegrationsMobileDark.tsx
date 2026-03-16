import IntegrationsMobile from "../../imports/IntegrationsMobile";

export default function IntegrationsMobileDark() {
  return (
    <div className="size-full bg-[#0a0a0b] overflow-auto">
      <div className="min-h-full dark-theme-wrapper-mobile">
        <style>{`
          .dark-theme-wrapper-mobile {
            --fill-0: white;
            --stroke-0: white;
          }

          /* Header and navigation */
          .dark-theme-wrapper-mobile [data-name="Header"],
          .dark-theme-wrapper-mobile [data-name="Navbar"],
          .dark-theme-wrapper-mobile [data-name*="Nav"] {
            background: rgba(255, 255, 255, 0.03) !important;
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          }

          /* All white backgrounds become dark */
          .dark-theme-wrapper-mobile .bg-white {
            background: transparent !important;
          }

          /* Section containers should be fully transparent */
          .dark-theme-wrapper-mobile > div > div > div.bg-white {
            background: transparent !important;
          }

          /* Text colors - all black text becomes white */
          .dark-theme-wrapper-mobile .text-black,
          .dark-theme-wrapper-mobile [style*="text-black"],
          .dark-theme-wrapper-mobile p:not([class*="text-white"]):not([class*="text-gray"]) {
            color: white !important;
          }

          /* Headings use Inter Bold */
          .dark-theme-wrapper-mobile [class*="Roboto:Bold"],
          .dark-theme-wrapper-mobile [style*="font-['Roboto:Bold"] {
            font-family: 'Inter', sans-serif !important;
            font-weight: 800 !important;
          }

          /* Semi-bold becomes bold Inter */
          .dark-theme-wrapper-mobile [class*="Roboto:SemiBold"],
          .dark-theme-wrapper-mobile [style*="font-['Roboto:SemiBold"] {
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
          }

          /* Regular text uses Inter */
          .dark-theme-wrapper-mobile [class*="Roboto:Regular"],
          .dark-theme-wrapper-mobile [style*="font-['Roboto:Regular"] {
            font-family: 'Inter', sans-serif !important;
            font-weight: 400 !important;
          }

          /* Body text in gray */
          .dark-theme-wrapper-mobile [class*="Roboto:Regular"][style*="text-[16px]"]:not([data-name*="Button"] *),
          .dark-theme-wrapper-mobile [class*="Roboto:Regular"][style*="text-[14px]"]:not([data-name*="Button"] *),
          .dark-theme-wrapper-mobile [class*="Roboto:Regular"][style*="text-[12px]"]:not([data-name*="Button"] *) {
            color: #d1d5db !important;
          }

          /* Remove glassmorphic styling from broad containers - keep backgrounds black/transparent */
          .dark-theme-wrapper-mobile [data-name*="Layout"],
          .dark-theme-wrapper-mobile [data-name*="Section"]:not([data-name*="Card"]) {
            background: transparent !important;
          }

          /* Only apply glassmorphic cards to specific card elements */
          .dark-theme-wrapper-mobile [data-name*="Integration Card"],
          .dark-theme-wrapper-mobile [data-name*="Feature Card"],
          .dark-theme-wrapper-mobile [data-name*="Tool Card"],
          .dark-theme-wrapper-mobile [data-name*="Platform Card"] {
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 20px !important;
          }

          /* Hero sections */
          .dark-theme-wrapper-mobile [data-name*="Hero"],
          .dark-theme-wrapper-mobile [data-name*="Header /"] {
            background: rgba(255, 255, 255, 0.02) !important;
          }

          /* Primary buttons - black becomes #00ffc2 */
          .dark-theme-wrapper-mobile .bg-black,
          .dark-theme-wrapper-mobile [data-name="Button"] .bg-black {
            background: #00ffc2 !important;
            border-color: #00ffc2 !important;
            border-radius: 8px !important;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper-mobile .bg-black p,
          .dark-theme-wrapper-mobile .bg-black .text-white {
            color: #0a0a0b !important;
            font-weight: 600 !important;
          }

          /* Secondary buttons */
          .dark-theme-wrapper-mobile [data-name="Button"]:not(:has(.bg-black)) {
            border-color: #4b5563 !important;
            background: transparent !important;
            border-radius: 8px !important;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper-mobile [data-name="Button"]:not(:has(.bg-black)):active {
            border-color: #00ffc2 !important;
            background: rgba(0, 255, 194, 0.1) !important;
          }

          /* Border colors */
          .dark-theme-wrapper-mobile .border-black,
          .dark-theme-wrapper-mobile [aria-hidden="true"].border-black {
            border-color: #4b5563 !important;
          }

          /* SVG icons */
          .dark-theme-wrapper-mobile svg path[fill*="black"],
          .dark-theme-wrapper-mobile svg path[id*="Vector"]:not([data-name*="Logo"] *) {
            fill: #00ffc2 !important;
          }

          .dark-theme-wrapper-mobile svg circle[stroke*="black"],
          .dark-theme-wrapper-mobile svg path[stroke*="black"] {
            stroke: #00ffc2 !important;
          }

          /* Logo icons stay white */
          .dark-theme-wrapper-mobile [data-name*="Logo"] svg path,
          .dark-theme-wrapper-mobile [data-name="Logo-wide 1"] svg path {
            fill: white !important;
          }

          /* Integration/Platform cards */
          .dark-theme-wrapper-mobile [data-name*="Platform"],
          .dark-theme-wrapper-mobile [data-name*="Company"],
          .dark-theme-wrapper-mobile [data-name*="Tool Card"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper-mobile [data-name*="Platform"]:active,
          .dark-theme-wrapper-mobile [data-name*="Tool Card"]:active {
            background: rgba(0, 255, 194, 0.05) !important;
            border-color: rgba(0, 255, 194, 0.3) !important;
          }

          /* Category sections */
          .dark-theme-wrapper-mobile [data-name*="Category"],
          .dark-theme-wrapper-mobile [data-name*="Section"] {
            background: rgba(255, 255, 255, 0.02) !important;
            border-radius: 16px !important;
          }

          /* Icon containers */
          .dark-theme-wrapper-mobile [data-name*="Icon"] {
            background: rgba(0, 255, 194, 0.1) !important;
            border-radius: 12px;
            padding: 10px;
          }

          /* CTA sections */
          .dark-theme-wrapper-mobile [data-name*="Cta"],
          .dark-theme-wrapper-mobile [data-name*="CTA"],
          .dark-theme-wrapper-mobile [data-name*="Request"] {
            background: rgba(0, 255, 194, 0.05) !important;
            border: 1px solid rgba(0, 255, 194, 0.2) !important;
            border-radius: 20px !important;
          }

          /* Links */
          .dark-theme-wrapper-mobile a {
            color: #d1d5db !important;
            transition: color 0.2s;
          }

          .dark-theme-wrapper-mobile a:active {
            color: #00ffc2 !important;
          }

          /* Taglines and labels */
          .dark-theme-wrapper-mobile [data-name*="Tagline"] p,
          .dark-theme-wrapper-mobile [data-name*="Tag"] p,
          .dark-theme-wrapper-mobile [data-name*="Label"] p {
            color: #00ffc2 !important;
            font-weight: 600 !important;
          }

          /* Images */
          .dark-theme-wrapper-mobile img {
            border-radius: 12px;
            opacity: 0.75;
          }

          /* Footer */
          .dark-theme-wrapper-mobile [data-name="Footer"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
          }

          .dark-theme-wrapper-mobile [data-name="Footer"] p,
          .dark-theme-wrapper-mobile [data-name="Footer"] a {
            color: #9ca3af !important;
          }

          /* Input fields */
          .dark-theme-wrapper-mobile input,
          .dark-theme-wrapper-mobile textarea {
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border-radius: 8px;
          }

          .dark-theme-wrapper-mobile input::placeholder,
          .dark-theme-wrapper-mobile textarea::placeholder {
            color: #6b7280 !important;
          }

          .dark-theme-wrapper-mobile input:focus,
          .dark-theme-wrapper-mobile textarea:focus {
            border-color: #00ffc2 !important;
            outline: none;
            box-shadow: 0 0 0 3px rgba(0, 255, 194, 0.1);
          }

          /* Menu overlay */
          .dark-theme-wrapper-mobile [data-name*="Menu"],
          .dark-theme-wrapper-mobile [data-name*="Sidebar"] {
            background: rgba(10, 10, 11, 0.98) !important;
            backdrop-filter: blur(20px);
          }

          /* Hamburger icon */
          .dark-theme-wrapper-mobile [data-name*="Hamburger"] svg path,
          .dark-theme-wrapper-mobile [data-name*="Menu Icon"] svg path {
            stroke: white !important;
          }

          /* Dividers */
          .dark-theme-wrapper-mobile hr,
          .dark-theme-wrapper-mobile [data-name*="Divider"] {
            border-color: rgba(255, 255, 255, 0.1) !important;
          }

          /* Badges */
          .dark-theme-wrapper-mobile [data-name*="Badge"],
          .dark-theme-wrapper-mobile [data-name*="Indicator"] {
            background: rgba(0, 255, 194, 0.1) !important;
            border: 1px solid rgba(0, 255, 194, 0.3) !important;
            color: #00ffc2 !important;
            border-radius: 6px;
            padding: 4px 10px;
          }

          /* Tab navigation */
          .dark-theme-wrapper-mobile [data-name*="Tab"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper-mobile [data-name*="Tab"]:active,
          .dark-theme-wrapper-mobile [data-name*="Tab"][data-state="active"] {
            background: rgba(0, 255, 194, 0.1) !important;
            border-color: #00ffc2 !important;
          }

          /* Grid layouts */
          .dark-theme-wrapper-mobile [data-name*="Grid"] {
            gap: 16px;
          }

          /* List items */
          .dark-theme-wrapper-mobile [data-name*="List Item"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            padding: 12px;
          }
        `}</style>
        <IntegrationsMobile />
      </div>
    </div>
  );
}
