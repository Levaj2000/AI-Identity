import SecurityDesktop from "../../imports/SecurityDesktop";

export default function SecurityDark() {
  return (
    <div className="size-full bg-[#0a0a0b] overflow-auto">
      <div className="min-h-full dark-theme-wrapper">
        <style>{`
          .dark-theme-wrapper {
            /* Override all fill colors */
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

          /* All white backgrounds become dark */
          .dark-theme-wrapper .bg-white {
            background: transparent !important;
          }

          /* Section containers should be fully transparent */
          .dark-theme-wrapper > div > div > div.bg-white {
            background: transparent !important;
          }

          /* Text colors - all black text becomes white */
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
          .dark-theme-wrapper [class*="Roboto:Regular"][style*="text-[16px]"],
          .dark-theme-wrapper [class*="Roboto:Regular"][style*="text-[14px]"] {
            color: #d1d5db !important;
          }

          /* Remove glassmorphic styling from broad containers - keep backgrounds black/transparent */
          .dark-theme-wrapper [data-name*="Layout"],
          .dark-theme-wrapper [data-name*="Section"]:not([data-name*="Card"]) {
            background: transparent !important;
          }

          /* Only apply glassmorphic styling to actual card components */
          .dark-theme-wrapper [data-name*="Feature Card"],
          .dark-theme-wrapper [data-name*="Platform Card"],
          .dark-theme-wrapper [data-name*="Question"] {
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 20px !important;
          }

          /* Primary buttons - black becomes #00ffc2 */
          .dark-theme-wrapper .bg-black,
          .dark-theme-wrapper [data-name="Button"] .bg-black {
            background: #00ffc2 !important;
            border-color: #00ffc2 !important;
            border-radius: 8px !important;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper .bg-black:hover {
            background: #00e6ad !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 255, 194, 0.3);
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
            border-radius: 8px !important;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper [data-name="Button"]:not(:has(.bg-black)):hover {
            border-color: #00ffc2 !important;
            background: rgba(0, 255, 194, 0.1) !important;
            transform: translateY(-1px);
          }

          .dark-theme-wrapper [data-name="Button"]:not(:has(.bg-black)) p {
            color: white !important;
          }

          /* Border colors */
          .dark-theme-wrapper .border-black,
          .dark-theme-wrapper [aria-hidden="true"].border-black {
            border-color: #4b5563 !important;
          }

          /* SVG icons - accent color */
          .dark-theme-wrapper svg path[fill*="black"],
          .dark-theme-wrapper svg path[id*="Vector"]:not([data-name*="Logo"] *) {
            fill: #00ffc2 !important;
          }

          .dark-theme-wrapper svg circle[stroke*="black"],
          .dark-theme-wrapper svg path[stroke*="black"] {
            stroke: #00ffc2 !important;
          }

          /* Logo icons stay white */
          .dark-theme-wrapper [data-name*="Logo"] svg path,
          .dark-theme-wrapper [data-name="Logo-wide 1"] svg path {
            fill: white !important;
          }

          /* Platform logos in cards */
          .dark-theme-wrapper [data-name*="Platform"] img,
          .dark-theme-wrapper [data-name*="Logo"] img {
            filter: brightness(0) invert(1);
            opacity: 0.9;
          }

          /* Platform cards */
          .dark-theme-wrapper [data-name*="Platform"],
          .dark-theme-wrapper [data-name*="Company"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            padding: 16px;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper [data-name*="Platform"]:hover,
          .dark-theme-wrapper [data-name*="Company"]:hover {
            background: rgba(0, 255, 194, 0.05) !important;
            border-color: rgba(0, 255, 194, 0.3) !important;
            transform: translateY(-2px);
          }

          /* Three pillars section */
          .dark-theme-wrapper [data-name*="Pillar"] {
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 20px !important;
            padding: 32px;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper [data-name*="Pillar"]:hover {
            background: rgba(0, 255, 194, 0.05) !important;
            border-color: rgba(0, 255, 194, 0.2) !important;
            transform: translateY(-4px);
          }

          /* Icon containers */
          .dark-theme-wrapper [data-name*="Icon"] {
            background: rgba(0, 255, 194, 0.1) !important;
            border-radius: 12px;
            padding: 12px;
          }

          /* FAQ/Questions section */
          .dark-theme-wrapper [data-name*="Question"],
          .dark-theme-wrapper [data-name*="FAQ"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 16px !important;
            padding: 24px;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper [data-name*="Question"]:hover {
            background: rgba(255, 255, 255, 0.05) !important;
            border-color: rgba(0, 255, 194, 0.2) !important;
          }

          /* CTA sections */
          .dark-theme-wrapper [data-name*="Cta"],
          .dark-theme-wrapper [data-name*="CTA"],
          .dark-theme-wrapper [data-name*="Request"] {
            background: rgba(0, 255, 194, 0.05) !important;
            border: 1px solid rgba(0, 255, 194, 0.2) !important;
            border-radius: 24px !important;
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
          .dark-theme-wrapper [data-name*="Tag"] p,
          .dark-theme-wrapper [data-name*="Label"] p {
            color: #00ffc2 !important;
            font-weight: 600 !important;
          }

          /* Images and placeholders */
          .dark-theme-wrapper img {
            border-radius: 16px;
            opacity: 0.75;
          }

          /* Section backgrounds */
          .dark-theme-wrapper [data-name*="Section"],
          .dark-theme-wrapper [data-name*="Layout"] {
            background: transparent !important;
          }

          /* Footer */
          .dark-theme-wrapper [data-name="Footer"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
          }

          .dark-theme-wrapper [data-name="Footer"] p,
          .dark-theme-wrapper [data-name="Footer"] a {
            color: #9ca3af !important;
          }

          .dark-theme-wrapper [data-name="Footer"] a:hover {
            color: #00ffc2 !important;
          }

          /* Input fields */
          .dark-theme-wrapper input,
          .dark-theme-wrapper textarea {
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border-radius: 8px;
          }

          .dark-theme-wrapper input::placeholder,
          .dark-theme-wrapper textarea::placeholder {
            color: #6b7280 !important;
          }

          .dark-theme-wrapper input:focus,
          .dark-theme-wrapper textarea:focus {
            border-color: #00ffc2 !important;
            outline: none;
            box-shadow: 0 0 0 3px rgba(0, 255, 194, 0.1);
          }

          /* Grid and list items */
          .dark-theme-wrapper [data-name*="Grid Item"],
          .dark-theme-wrapper [data-name*="List Item"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 16px !important;
            padding: 24px;
            transition: all 0.3s ease;
          }

          .dark-theme-wrapper [data-name*="Grid Item"]:hover,
          .dark-theme-wrapper [data-name*="List Item"]:hover {
            background: rgba(0, 255, 194, 0.05) !important;
            border-color: rgba(0, 255, 194, 0.2) !important;
            transform: translateY(-2px);
          }

          /* Security badges and indicators */
          .dark-theme-wrapper [data-name*="Badge"],
          .dark-theme-wrapper [data-name*="Indicator"] {
            background: rgba(0, 255, 194, 0.1) !important;
            border: 1px solid rgba(0, 255, 194, 0.3) !important;
            color: #00ffc2 !important;
            border-radius: 8px;
            padding: 6px 12px;
          }

          /* Dividers */
          .dark-theme-wrapper hr,
          .dark-theme-wrapper [data-name*="Divider"] {
            border-color: rgba(255, 255, 255, 0.1) !important;
          }

          /* Feature icons with glow effect */
          .dark-theme-wrapper [data-name*="security"],
          .dark-theme-wrapper [data-name*="shield"],
          .dark-theme-wrapper [data-name*="lock"] {
            filter: drop-shadow(0 0 8px rgba(0, 255, 194, 0.3));
          }

          /* Subtle accent on hover for all interactive cards */
          .dark-theme-wrapper [data-name*="Card"]:hover,
          .dark-theme-wrapper [data-name*="Feature"]:hover {
            box-shadow: 0 8px 24px rgba(0, 255, 194, 0.1);
          }

          /* Section headers and titles */
          .dark-theme-wrapper [data-name*="Section Title"] h1,
          .dark-theme-wrapper [data-name*="Section Title"] h2,
          .dark-theme-wrapper [data-name*="Section Title"] p[class*="text-[48px]"],
          .dark-theme-wrapper [data-name*="Section Title"] p[class*="text-[56px]"] {
            background: linear-gradient(135deg, #ffffff 0%, #e5e7eb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
          }
        `}</style>
        <SecurityDesktop />
      </div>
    </div>
  );
}
