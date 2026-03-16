import svgPaths from "./svg-yz1l0xpjex";
import { AIIdentityLogo5 } from "../app/components/AIIdentityLogo";
import imgPlaceholderImage from "figma:asset/d568b164c26b35eebe6a407c03f478bc8049c84b.png";

function LogoWide() {
  return (
    <div className="-translate-x-1/2 -translate-y-1/2 absolute h-[36px] left-[calc(50%-0.33px)] top-1/2 w-[70px]" data-name="Logo-wide 1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 70 36">
        <g clipPath="url(#clip0_1_772)" id="Logo-wide 1">
          <path d={svgPaths.p2a3a6680} fill="var(--fill-0, black)" id="Vector" />
          <path d={svgPaths.p611b180} fill="var(--fill-0, black)" id="Vector_2" />
          <path d={svgPaths.pf19e700} fill="var(--fill-0, black)" id="Vector_3" />
          <path d={svgPaths.p3342b000} fill="var(--fill-0, black)" id="Vector_4" />
          <path clipRule="evenodd" d={svgPaths.p16e9bf00} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector_5" />
        </g>
        <defs>
          <clipPath id="clip0_1_772">
            <rect fill="white" height="36" width="70" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Content1() {
  return (
    <div className="content-stretch flex items-center relative shrink-0" data-name="Content">
      <div className="h-[36px] overflow-clip relative shrink-0 w-[84px]" data-name="Company Logo">
        <LogoWide />
      </div>
    </div>
  );
}

function Icon() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 size-[48px]" data-name="Icon">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="close">
        <div className="absolute inset-[22.6%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.15 13.15">
            <path d={svgPaths.p23282800} fill="var(--fill-0, black)" id="Vector" stroke="var(--stroke-0, black)" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Content() {
  return (
    <div className="h-[64px] relative shrink-0 w-full" data-name="Content">
      <div className="flex flex-row items-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex items-center justify-between pl-[20px] pr-[12px] relative size-full">
          <Content1 />
          <Icon />
        </div>
      </div>
    </div>
  );
}

function Link() {
  return (
    <div className="content-stretch flex items-start py-[12px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[16px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        How it works
      </p>
    </div>
  );
}

function Link1() {
  return (
    <div className="content-stretch flex items-start py-[12px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[16px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Integrations
      </p>
    </div>
  );
}

function Link2() {
  return (
    <div className="content-stretch flex items-start py-[12px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal h-[24px] leading-[1.5] min-h-px min-w-px relative text-[16px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Security
      </p>
    </div>
  );
}

function ChevronDown() {
  return (
    <div className="relative shrink-0 size-[24px]" data-name="Chevron Down">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24 24">
        <g id="Chevron Down">
          <path clipRule="evenodd" d={svgPaths.pee47f00} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
        </g>
      </svg>
    </div>
  );
}

function NavLinkDropdown() {
  return (
    <div className="content-stretch flex flex-[1_0_0] gap-[16px] items-center min-h-px min-w-px relative" data-name="Nav Link Dropdown">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[16px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Resources
      </p>
      <ChevronDown />
    </div>
  );
}

function Link3() {
  return (
    <div className="content-stretch flex items-start py-[12px] relative shrink-0 w-full" data-name="Link">
      <NavLinkDropdown />
    </div>
  );
}

function Content2() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Proxy gateway
      </p>
    </div>
  );
}

function MenuItem() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content2 />
    </div>
  );
}

function Content3() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        API reference
      </p>
    </div>
  );
}

function MenuItem1() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content3 />
    </div>
  );
}

function Content4() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Fail-closed security
      </p>
    </div>
  );
}

function MenuItem2() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content4 />
    </div>
  );
}

function Content5() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Framework support
      </p>
    </div>
  );
}

function MenuItem3() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content5 />
    </div>
  );
}

function List() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-start relative shrink-0" data-name="List">
      <MenuItem />
      <MenuItem1 />
      <MenuItem2 />
      <MenuItem3 />
    </div>
  );
}

function MenuList() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-start relative shrink-0 w-full" data-name="Menu List">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] min-w-full relative shrink-0 text-[14px] text-black w-[min-content]" style={{ fontVariationSettings: "'wdth' 100" }}>
        Platform
      </p>
      <List />
    </div>
  );
}

function Content6() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Get started
      </p>
    </div>
  );
}

function MenuItem4() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content6 />
    </div>
  );
}

function Content7() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Documentation
      </p>
    </div>
  );
}

function MenuItem5() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content7 />
    </div>
  );
}

function Content8() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Code samples
      </p>
    </div>
  );
}

function MenuItem6() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content8 />
    </div>
  );
}

function Content9() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Community
      </p>
    </div>
  );
}

function MenuItem7() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content9 />
    </div>
  );
}

function List1() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-start relative shrink-0" data-name="List">
      <MenuItem4 />
      <MenuItem5 />
      <MenuItem6 />
      <MenuItem7 />
    </div>
  );
}

function MenuList1() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-start relative shrink-0 w-full" data-name="Menu List">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] min-w-full relative shrink-0 text-[14px] text-black w-[min-content]" style={{ fontVariationSettings: "'wdth' 100" }}>
        Developers
      </p>
      <List1 />
    </div>
  );
}

function Content10() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        About us
      </p>
    </div>
  );
}

function MenuItem8() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content10 />
    </div>
  );
}

function Content11() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Blog
      </p>
    </div>
  );
}

function MenuItem9() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content11 />
    </div>
  );
}

function Content12() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Contact
      </p>
    </div>
  );
}

function MenuItem10() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content12 />
    </div>
  );
}

function Content13() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Careers
      </p>
    </div>
  );
}

function MenuItem11() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content13 />
    </div>
  );
}

function List2() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-start relative shrink-0" data-name="List">
      <MenuItem8 />
      <MenuItem9 />
      <MenuItem10 />
      <MenuItem11 />
    </div>
  );
}

function MenuList2() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-start relative shrink-0 w-full" data-name="Menu List">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] min-w-full relative shrink-0 text-[14px] text-black w-[min-content]" style={{ fontVariationSettings: "'wdth' 100" }}>
        Company
      </p>
      <List2 />
    </div>
  );
}

function Content14() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-[276px]" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Privacy
      </p>
    </div>
  );
}

function MenuItem12() {
  return (
    <div className="content-stretch flex gap-[12px] items-start py-[8px] relative shrink-0" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content14 />
    </div>
  );
}

function Content15() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Terms
      </p>
    </div>
  );
}

function MenuItem13() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content15 />
    </div>
  );
}

function Content16() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Security
      </p>
    </div>
  );
}

function MenuItem14() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content16 />
    </div>
  );
}

function Content17() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col items-start min-h-px min-w-px relative" data-name="Content">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Compliance
      </p>
    </div>
  );
}

function MenuItem15() {
  return (
    <div className="content-stretch flex gap-[12px] h-[40px] items-start py-[8px] relative shrink-0 w-[335px]" data-name="Menu Item">
      <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
        <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
            <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
          </svg>
        </div>
      </div>
      <Content17 />
    </div>
  );
}

function List3() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-start relative shrink-0" data-name="List">
      <MenuItem12 />
      <MenuItem13 />
      <MenuItem14 />
      <MenuItem15 />
    </div>
  );
}

function MenuList3() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-start relative shrink-0 w-full" data-name="Menu List">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] min-w-full relative shrink-0 text-[14px] text-black w-[min-content]" style={{ fontVariationSettings: "'wdth' 100" }}>
        Legal
      </p>
      <List3 />
    </div>
  );
}

function Menu() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start py-[16px] relative shrink-0 w-full" data-name="Menu">
      <MenuList />
      <MenuList1 />
      <MenuList2 />
      <MenuList3 />
    </div>
  );
}

function Content19() {
  return (
    <div className="content-stretch flex flex-col font-['Roboto:Regular',sans-serif] font-normal gap-[16px] items-start leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" data-name="Content">
      <p className="relative shrink-0" style={{ fontVariationSettings: "'wdth' 100" }}>
        Ready to begin?
      </p>
      <p className="[text-decoration-skip-ink:none] decoration-solid relative shrink-0 underline" style={{ fontVariationSettings: "'wdth' 100" }}>
        Start building now
      </p>
    </div>
  );
}

function Content20() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-center relative shrink-0 w-full" data-name="Content">
      <div className="content-stretch flex gap-[8px] items-center justify-center py-[4px] relative shrink-0 w-full" data-name="Sign up action 1">
        <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
          <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
              <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
            </svg>
          </div>
        </div>
        <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
          Sign in
        </p>
      </div>
      <div className="content-stretch flex gap-[8px] items-center justify-center py-[4px] relative shrink-0 w-full" data-name="Sign up action 2">
        <div className="overflow-clip relative shrink-0 size-[24px]" data-name="Relume">
          <div className="absolute inset-[8.33%_12.5%]" data-name="Vector">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 20.0001">
              <path clipRule="evenodd" d={svgPaths.p2854d800} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector" />
            </svg>
          </div>
        </div>
        <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
          Contact
        </p>
      </div>
    </div>
  );
}

function Content18() {
  return (
    <div className="bg-white relative shrink-0 w-full" data-name="Content">
      <div className="content-stretch flex flex-col gap-[16px] items-start p-[24px] relative w-full">
        <Content19 />
        <Content20 />
      </div>
    </div>
  );
}

function MegaMenu() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Mega Menu 1">
      <Menu />
      <Content18 />
    </div>
  );
}

function Row1() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Row">
      <Link3 />
      <MegaMenu />
    </div>
  );
}

function Column() {
  return (
    <div className="content-stretch flex flex-col items-start overflow-clip relative shrink-0 w-full" data-name="Column">
      <Link />
      <Link1 />
      <Link2 />
      <Row1 />
    </div>
  );
}

function Actions() {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-start pb-[80px] pt-[24px] relative shrink-0 w-full" data-name="Actions">
      <div className="relative shrink-0 w-full" data-name="Button">
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
        <div className="flex flex-row items-center justify-center size-full">
          <div className="content-stretch flex items-center justify-center px-[20px] py-[8px] relative w-full">
            <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
              Demo
            </p>
          </div>
        </div>
      </div>
      <div className="bg-black relative shrink-0 w-full" data-name="Button">
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
        <div className="flex flex-row items-center justify-center size-full">
          <div className="content-stretch flex items-center justify-center px-[20px] py-[8px] relative w-full">
            <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-white whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
              Start
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row() {
  return (
    <div className="relative shrink-0 w-full" data-name="Row">
      <div className="overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-start pb-[80px] pt-[16px] px-[20px] relative w-full">
          <Column />
          <Actions />
        </div>
      </div>
    </div>
  );
}

function Navbar() {
  return (
    <div className="bg-white content-stretch flex flex-col items-center overflow-clip relative shrink-0 w-full" data-name="Navbar / 7 /">
      <Content />
      <Row />
    </div>
  );
}

function TaglineWrapper() {
  return (
    <div className="content-stretch flex items-center relative shrink-0 w-full" data-name="Tagline Wrapper">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black text-center whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
        Protection
      </p>
    </div>
  );
}

function Content21() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-center relative shrink-0 text-black text-center w-full" data-name="Content">
      <p className="font-['Roboto:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[40px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Agents need armor
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Non-human identities demand the same rigor as human ones. SOC 2-ready architecture with HMAC-chained audit logs—compliance isn't a roadmap item, it's built-in from day one.
      </p>
    </div>
  );
}

function SectionTitle() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-center relative shrink-0 w-full" data-name="Section Title">
      <TaglineWrapper />
      <Content21 />
    </div>
  );
}

function Actions1() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0" data-name="Actions">
      <div className="bg-black content-stretch flex items-center justify-center px-[24px] py-[12px] relative shrink-0" data-name="Button">
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
        <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-white whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
          Explore
        </p>
      </div>
      <div className="content-stretch flex items-center justify-center px-[24px] py-[12px] relative shrink-0" data-name="Button">
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
        <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
          Learn
        </p>
      </div>
    </div>
  );
}

function Component() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-center max-w-[768px] relative shrink-0 w-full" data-name="Component">
      <SectionTitle />
      <Actions1 />
    </div>
  );
}

function Container() {
  return (
    <div className="content-stretch flex flex-col items-center max-w-[1280px] relative shrink-0 w-full" data-name="Container">
      <Component />
    </div>
  );
}

function Header() {
  return (
    <div className="bg-white relative shrink-0 w-full" data-name="Header / 62 /">
      <div className="flex flex-col items-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-center px-[20px] py-[64px] relative w-full">
          <Container />
        </div>
      </div>
    </div>
  );
}

function TaglineWrapper1() {
  return (
    <div className="content-stretch flex items-center relative shrink-0" data-name="Tagline Wrapper">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
        Certainty
      </p>
    </div>
  );
}

function Content24() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-start relative shrink-0 text-black w-full" data-name="Content">
      <p className="font-['Roboto:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[36px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        When doubt arrives, security prevails
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Fail-closed means your agent defaults to the safest state when uncertainty emerges. No guessing. No compromise.
      </p>
    </div>
  );
}

function SectionTitle1() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full" data-name="Section Title">
      <TaglineWrapper1 />
      <Content24 />
    </div>
  );
}

function Logos() {
  return (
    <div className="content-start flex flex-wrap gap-[24px_32px] items-start py-[8px] relative shrink-0 w-full" data-name="Logos">
      <div className="h-[48px] overflow-clip relative shrink-0 w-[119.999px]" data-name="Placeholder Logo">
        <div className="-translate-x-1/2 -translate-y-1/2 absolute h-[19.286px] left-[calc(50%-0.01px)] top-1/2 w-[115.697px]" data-name="Logo">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 115.697 19.2857">
            <g id="Logo">
              <path clipRule="evenodd" d={svgPaths.p10d07e00} fill="var(--fill-0, black)" fillRule="evenodd" />
              <path d={svgPaths.p31e400c0} fill="var(--fill-0, black)" />
              <path clipRule="evenodd" d={svgPaths.p11f57780} fill="var(--fill-0, black)" fillRule="evenodd" />
              <path d={svgPaths.p29c87af0} fill="var(--fill-0, black)" />
              <path clipRule="evenodd" d={svgPaths.p3f20c0c0} fill="var(--fill-0, black)" fillRule="evenodd" />
              <path d={svgPaths.p32e45040} fill="var(--fill-0, black)" />
              <path clipRule="evenodd" d={svgPaths.p49d8c00} fill="var(--fill-0, black)" fillRule="evenodd" />
              <path d={svgPaths.p15128500} fill="var(--fill-0, black)" />
            </g>
          </svg>
        </div>
      </div>
      <div className="h-[48px] overflow-clip relative shrink-0 w-[119.999px]" data-name="Placeholder Logo">
        <div className="-translate-x-1/2 -translate-y-1/2 absolute h-[30.75px] left-[calc(50%+0.22px)] top-[calc(50%+0.38px)] w-[113.584px]" data-name="Logo">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 113.584 30.7498">
            <path clipRule="evenodd" d={svgPaths.p19de50c0} fill="var(--fill-0, black)" fillRule="evenodd" id="Logo" />
          </svg>
        </div>
      </div>
      <div className="h-[48px] overflow-clip relative shrink-0 w-[119.999px]" data-name="Placeholder Logo">
        <div className="-translate-x-1/2 -translate-y-1/2 absolute h-[19.286px] left-[calc(50%-0.01px)] top-1/2 w-[115.697px]" data-name="Logo">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 115.697 19.2857">
            <g id="Logo">
              <path clipRule="evenodd" d={svgPaths.p10d07e00} fill="var(--fill-0, black)" fillRule="evenodd" />
              <path d={svgPaths.p31e400c0} fill="var(--fill-0, black)" />
              <path clipRule="evenodd" d={svgPaths.p11f57780} fill="var(--fill-0, black)" fillRule="evenodd" />
              <path d={svgPaths.p29c87af0} fill="var(--fill-0, black)" />
              <path clipRule="evenodd" d={svgPaths.p3f20c0c0} fill="var(--fill-0, black)" fillRule="evenodd" />
              <path d={svgPaths.p32e45040} fill="var(--fill-0, black)" />
              <path clipRule="evenodd" d={svgPaths.p49d8c00} fill="var(--fill-0, black)" fillRule="evenodd" />
              <path d={svgPaths.p15128500} fill="var(--fill-0, black)" />
            </g>
          </svg>
        </div>
      </div>
      <div className="h-[48px] overflow-clip relative shrink-0 w-[119.999px]" data-name="Placeholder Logo">
        <div className="-translate-x-1/2 -translate-y-1/2 absolute h-[30.75px] left-[calc(50%+0.22px)] top-[calc(50%+0.38px)] w-[113.584px]" data-name="Logo">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 113.584 30.7498">
            <path clipRule="evenodd" d={svgPaths.p19de50c0} fill="var(--fill-0, black)" fillRule="evenodd" id="Logo" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Content23() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-start relative shrink-0 w-full" data-name="Content">
      <SectionTitle1 />
      <Logos />
    </div>
  );
}

function Actions2() {
  return (
    <div className="content-stretch flex gap-[24px] items-center relative shrink-0" data-name="Actions">
      <div className="relative shrink-0" data-name="Button">
        <div className="content-stretch flex items-center justify-center overflow-clip px-[24px] py-[12px] relative rounded-[inherit]">
          <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
            Learn
          </p>
        </div>
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
      </div>
      <div className="content-stretch flex gap-[8px] items-center justify-center overflow-clip relative shrink-0" data-name="Button">
        <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
          Read
        </p>
        <div className="overflow-clip relative shrink-0 size-[24px]" data-name="chevron_right">
          <div className="absolute inset-[25.72%_36.66%_25.88%_35.46%]" data-name="Vector">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6.69159 11.6166">
              <path d={svgPaths.p36daa800} fill="var(--fill-0, black)" id="Vector" stroke="var(--stroke-0, black)" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Content22() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 w-full" data-name="Content">
      <Content23 />
      <Actions2 />
    </div>
  );
}

function Component1() {
  return (
    <div className="content-stretch flex flex-col gap-[48px] items-start relative shrink-0 w-full" data-name="Component">
      <Content22 />
      <div className="aspect-[335/348] relative shrink-0 w-full" data-name="Placeholder Image">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPlaceholderImage} />
      </div>
    </div>
  );
}

function Container1() {
  return (
    <div className="content-stretch flex flex-col items-start max-w-[1280px] relative shrink-0 w-full" data-name="Container">
      <Component1 />
    </div>
  );
}

function Layout() {
  return (
    <div className="bg-white relative shrink-0 w-full" data-name="Layout / 13 /">
      <div className="flex flex-col items-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-center px-[20px] py-[64px] relative w-full">
          <Container1 />
        </div>
      </div>
    </div>
  );
}

function TaglineWrapper2() {
  return (
    <div className="content-stretch flex items-center relative shrink-0" data-name="Tagline Wrapper">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black text-center whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
        Fortified
      </p>
    </div>
  );
}

function Content25() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-center relative shrink-0 text-black text-center w-full" data-name="Content">
      <p className="font-['Roboto:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[36px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Three pillars hold the line
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>{`Each layer works independently. Together they form a wall that doesn't bend.`}</p>
    </div>
  );
}

function SectionTitle2() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-center max-w-[768px] relative shrink-0 w-full" data-name="Section Title">
      <TaglineWrapper2 />
      <Content25 />
    </div>
  );
}

function Content26() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-center relative shrink-0 text-black text-center w-full" data-name="Content">
      <p className="font-['Roboto:Bold',sans-serif] font-bold leading-[1.3] relative shrink-0 text-[24px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Zero trust architecture
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Every request verified. Every credential questioned. Nothing assumed.
      </p>
    </div>
  );
}

function Column1() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-center relative shrink-0 w-full" data-name="Column">
      <div className="relative shrink-0 size-[48px]" data-name="verified">
        <div className="absolute inset-[6.42%_4.43%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 43.746 41.8378">
            <path d={svgPaths.p3cf98300} fill="var(--fill-0, black)" id="Vector" />
          </svg>
        </div>
      </div>
      <Content26 />
    </div>
  );
}

function Content27() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-center relative shrink-0 text-black text-center w-full" data-name="Content">
      <p className="font-['Roboto:Bold',sans-serif] font-bold leading-[1.3] relative shrink-0 text-[24px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Continuous authentication
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Identity checked at every step, not just at the door.
      </p>
    </div>
  );
}

function Column2() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-center relative shrink-0 w-full" data-name="Column">
      <div className="relative shrink-0 size-[48px]" data-name="safety_check">
        <div className="absolute inset-[8.02%_16.02%_8.15%_16.04%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 32.61 40.236">
            <path d={svgPaths.p353a0580} fill="var(--fill-0, black)" id="Vector" />
          </svg>
        </div>
      </div>
      <Content27 />
    </div>
  );
}

function Content28() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-center relative shrink-0 text-black text-center w-full" data-name="Content">
      <p className="font-['Roboto:Bold',sans-serif] font-bold leading-[1.3] relative shrink-0 text-[24px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Tamper-evident logging
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        HMAC-SHA256 integrity chains make every log entry cryptographically verifiable. What happened stays honest. Alterations leave marks.
      </p>
    </div>
  );
}

function Column3() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-center relative shrink-0 w-full" data-name="Column">
      <div className="relative shrink-0 size-[48px]" data-name="bookmark">
        <div className="absolute inset-[11.33%_20.19%_15.16%_20.21%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 28.61 35.285">
            <path d={svgPaths.p3d01b500} fill="var(--fill-0, black)" id="Vector" />
          </svg>
        </div>
      </div>
      <Content28 />
    </div>
  );
}

function Row2() {
  return (
    <div className="content-stretch flex flex-col gap-[48px] items-center relative shrink-0 w-full" data-name="Row">
      <Column1 />
      <Column2 />
      <Column3 />
    </div>
  );
}

function Actions3() {
  return (
    <div className="content-stretch flex gap-[24px] items-center relative shrink-0" data-name="Actions">
      <div className="relative shrink-0" data-name="Button">
        <div className="content-stretch flex items-center justify-center overflow-clip px-[24px] py-[12px] relative rounded-[inherit]">
          <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
            Explore
          </p>
        </div>
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
      </div>
      <div className="content-stretch flex gap-[8px] items-center justify-center overflow-clip relative shrink-0" data-name="Button">
        <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
          Details
        </p>
        <div className="overflow-clip relative shrink-0 size-[24px]" data-name="chevron_right">
          <div className="absolute inset-[25.72%_36.66%_25.88%_35.46%]" data-name="Vector">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6.69159 11.6166">
              <path d={svgPaths.p36daa800} fill="var(--fill-0, black)" id="Vector" stroke="var(--stroke-0, black)" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Container2() {
  return (
    <div className="content-stretch flex flex-col gap-[48px] items-center max-w-[1280px] relative shrink-0 w-full" data-name="Container">
      <SectionTitle2 />
      <Row2 />
      <Actions3 />
    </div>
  );
}

function Layout1() {
  return (
    <div className="bg-white relative shrink-0 w-full" data-name="Layout / 237 /">
      <div className="flex flex-col items-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-center px-[20px] py-[64px] relative w-full">
          <Container2 />
        </div>
      </div>
    </div>
  );
}

function Content29() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-start relative shrink-0 text-black w-full" data-name="Content">
      <p className="font-['Roboto:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[36px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Questions
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Answers for those building with autonomous agents and identity.
      </p>
    </div>
  );
}

function Actions4() {
  return (
    <div className="content-stretch flex items-center relative shrink-0" data-name="Actions">
      <div className="content-stretch flex items-center justify-center px-[24px] py-[12px] relative shrink-0" data-name="Button">
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
        <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
          Contact
        </p>
      </div>
    </div>
  );
}

function SectionTitle3() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 w-full" data-name="Section Title">
      <Content29 />
      <Actions4 />
    </div>
  );
}

function ListItem() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full" data-name="List Item">
      <p className="font-['Roboto:Bold',sans-serif] font-bold relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Can identities be spoofed?
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Not here. Our zero trust model treats every claim as suspect until proven. Spoofing requires breaking multiple independent verification layers simultaneously, which is why we sleep well at night.
      </p>
    </div>
  );
}

function ListItem1() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full" data-name="List Item">
      <p className="font-['Roboto:Bold',sans-serif] font-bold relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        What happens after a breach?
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Fail-closed means your agent stops everything and defaults to safe. No cascading failures. No silent compromises. The system locks down until you decide what comes next.
      </p>
    </div>
  );
}

function ListItem2() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full" data-name="List Item">
      <p className="font-['Roboto:Bold',sans-serif] font-bold relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        How do you meet compliance?
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        HMAC-chained audit logs give you the immutable trail regulators demand. SOC 2 Type I ready today, not after fundraising. Every action recorded. Every change tracked. Documentation that holds up.
      </p>
    </div>
  );
}

function ListItem3() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full" data-name="List Item">
      <p className="font-['Roboto:Bold',sans-serif] font-bold relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Does this slow things down?
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>{`Security and speed aren't enemies here. Our architecture validates in milliseconds. You get both the protection and the performance your agents need.`}</p>
    </div>
  );
}

function ListItem4() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full" data-name="List Item">
      <p className="font-['Roboto:Bold',sans-serif] font-bold relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Can I integrate this easily?
      </p>
      <p className="font-['Roboto:Regular',sans-serif] font-normal relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Yes. We built for developers. Standard protocols. Clear documentation. Your framework works with us, not against us.
      </p>
    </div>
  );
}

function List4() {
  return (
    <div className="content-stretch flex flex-col gap-[40px] items-start leading-[1.5] overflow-clip relative shrink-0 text-[16px] text-black w-full" data-name="List">
      <ListItem />
      <ListItem1 />
      <ListItem2 />
      <ListItem3 />
      <ListItem4 />
    </div>
  );
}

function Component2() {
  return (
    <div className="content-stretch flex flex-col gap-[48px] items-start relative shrink-0 w-full" data-name="Component">
      <SectionTitle3 />
      <List4 />
    </div>
  );
}

function Container3() {
  return (
    <div className="content-stretch flex flex-col items-start max-w-[1280px] relative shrink-0 w-full" data-name="Container">
      <Component2 />
    </div>
  );
}

function Faq() {
  return (
    <div className="bg-white relative shrink-0 w-full" data-name="FAQ / 8 /">
      <div className="overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-start px-[20px] py-[64px] relative w-full">
          <Container3 />
        </div>
      </div>
    </div>
  );
}

function Heading() {
  return (
    <div className="content-stretch flex flex-col font-['Roboto:Bold',sans-serif] font-bold items-center leading-[1.2] relative shrink-0 text-[40px] w-full" data-name="Heading">
      <p className="relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Request the details
      </p>
      <p className="relative shrink-0 w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Security matters
      </p>
    </div>
  );
}

function Content30() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-center relative shrink-0 text-black text-center w-full" data-name="Content">
      <Heading />
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Get our whitepaper or schedule a review with our security team today.
      </p>
    </div>
  );
}

function Actions5() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0" data-name="Actions">
      <div className="bg-black content-stretch flex items-center justify-center px-[24px] py-[12px] relative shrink-0" data-name="Button">
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
        <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-white whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
          Request
        </p>
      </div>
      <div className="content-stretch flex items-center justify-center px-[24px] py-[12px] relative shrink-0" data-name="Button">
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
        <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
          Schedule
        </p>
      </div>
    </div>
  );
}

function Column4() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] h-[308px] items-center max-w-[768px] relative shrink-0 w-full" data-name="Column">
      <Content30 />
      <Actions5 />
    </div>
  );
}

function Container4() {
  return (
    <div className="content-stretch flex flex-col items-start max-w-[1280px] relative shrink-0 w-full" data-name="Container">
      <Column4 />
    </div>
  );
}

function Cta() {
  return (
    <div className="bg-white relative shrink-0 w-full" data-name="CTA / 57 /">
      <div className="flex flex-col items-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-center px-[20px] py-[64px] relative w-full">
          <Container4 />
        </div>
      </div>
    </div>
  );
}

function LogoWide1() {
  return (
    <div className="-translate-x-1/2 -translate-y-1/2 absolute h-[36px] left-[calc(50%-0.33px)] top-1/2 w-[70px]" data-name="Logo-wide 1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 70 36">
        <g clipPath="url(#clip0_1_772)" id="Logo-wide 1">
          <path d={svgPaths.p2a3a6680} fill="var(--fill-0, black)" id="Vector" />
          <path d={svgPaths.p611b180} fill="var(--fill-0, black)" id="Vector_2" />
          <path d={svgPaths.pf19e700} fill="var(--fill-0, black)" id="Vector_3" />
          <path d={svgPaths.p3342b000} fill="var(--fill-0, black)" id="Vector_4" />
          <path clipRule="evenodd" d={svgPaths.p16e9bf00} fill="var(--fill-0, black)" fillRule="evenodd" id="Vector_5" />
        </g>
        <defs>
          <clipPath id="clip0_1_772">
            <rect fill="white" height="36" width="70" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Form() {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-start relative shrink-0 w-full" data-name="Form">
      <div className="relative shrink-0 w-full" data-name="Text input">
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
        <div className="flex flex-row items-center size-full">
          <div className="content-stretch flex items-center p-[12px] relative w-full">
            <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[16px] text-[rgba(0,0,0,0.6)]" style={{ fontVariationSettings: "'wdth' 100" }}>
              Email
            </p>
          </div>
        </div>
      </div>
      <div className="relative shrink-0 w-full" data-name="Button">
        <div aria-hidden="true" className="absolute border border-black border-solid inset-[-1px] pointer-events-none" />
        <div className="flex flex-row items-center justify-center size-full">
          <div className="content-stretch flex items-center justify-center px-[24px] py-[12px] relative w-full">
            <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
              Subscribe
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Actions6() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full" data-name="Actions">
      <Form />
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[12px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        By subscribing you agree to our Privacy Policy and consent to receive updates.
      </p>
    </div>
  );
}

function Newsletter() {
  return (
    <div className="content-stretch flex flex-col gap-[20px] items-start relative shrink-0 w-full" data-name="Newsletter">
      <div className="h-[36px] overflow-clip relative shrink-0 w-auto" data-name="Company Logo">
        <AIIdentityLogo5 className="h-[36px] w-auto" variant="primary" />
      </div>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-w-full relative shrink-0 text-[16px] text-black w-[min-content]" style={{ fontVariationSettings: "'wdth' 100" }}>
        Get updates on new features and product releases.
      </p>
      <Actions6 />
    </div>
  );
}

function Link4() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        How it works
      </p>
    </div>
  );
}

function Link5() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Integrations
      </p>
    </div>
  );
}

function Link6() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Security
      </p>
    </div>
  );
}

function Link7() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Documentation
      </p>
    </div>
  );
}

function Link8() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Company
      </p>
    </div>
  );
}

function FooterLinks() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Footer Links">
      <Link4 />
      <Link5 />
      <Link6 />
      <Link7 />
      <Link8 />
    </div>
  );
}

function Column5() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start overflow-clip relative shrink-0 w-full" data-name="Column">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Product
      </p>
      <FooterLinks />
    </div>
  );
}

function Link9() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Blog
      </p>
    </div>
  );
}

function Link10() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Careers
      </p>
    </div>
  );
}

function Link11() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Contact
      </p>
    </div>
  );
}

function Link12() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Legal
      </p>
    </div>
  );
}

function Link13() {
  return (
    <div className="content-stretch flex items-start py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="flex-[1_0_0] font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] min-h-px min-w-px relative text-[14px] text-black" style={{ fontVariationSettings: "'wdth' 100" }}>
        Follow us
      </p>
    </div>
  );
}

function FooterLinks1() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Footer Links">
      <Link9 />
      <Link10 />
      <Link11 />
      <Link12 />
      <Link13 />
    </div>
  );
}

function Column6() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start overflow-clip relative shrink-0 w-full" data-name="Column">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        About us
      </p>
      <FooterLinks1 />
    </div>
  );
}

function Link14() {
  return (
    <div className="content-stretch flex gap-[12px] items-center py-[8px] relative shrink-0 w-full" data-name="Link">
      <div className="overflow-clip relative shrink-0 size-[21px]" data-name="LinkedIn">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="xMidYMid meet" viewBox="0 0 24 24">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" fill="black"/>
        </svg>
      </div>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[14px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
        LinkedIn
      </p>
    </div>
  );
}

function Link15() {
  return (
    <div className="content-stretch flex gap-[12px] items-center py-[8px] relative shrink-0 w-full" data-name="Link">
      <div className="overflow-clip relative shrink-0 size-[21px]" data-name="GitHub">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="xMidYMid meet" viewBox="0 0 24 24">
          <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" fill="black"/>
        </svg>
      </div>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[14px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
        GitHub
      </p>
    </div>
  );
}

function Link16() {
  return (
    <div className="content-stretch flex gap-[12px] items-center py-[8px] relative shrink-0 w-full" data-name="Link">
      <div className="overflow-clip relative shrink-0 size-[21px]" data-name="Discord">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="xMidYMid meet" viewBox="0 0 24 24">
          <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z" fill="black"/>
        </svg>
      </div>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[14px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
        Discord
      </p>
    </div>
  );
}

function Link17() {
  return (
    <div className="content-stretch flex gap-[12px] items-center py-[8px] relative shrink-0 w-full" data-name="Link">
      <div className="overflow-clip relative shrink-0 size-[21px]" data-name="YouTube">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="xMidYMid meet" viewBox="0 0 24 24">
          <path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" fill="black"/>
        </svg>
      </div>
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[14px] text-black whitespace-nowrap" style={{ fontVariationSettings: "'wdth' 100" }}>
        YouTube
      </p>
    </div>
  );
}

function Link18() {
  return (
    <div className="content-stretch flex gap-[12px] items-center py-[8px] relative shrink-0 w-full" data-name="Link">
      <p className="font-['Roboto:Regular',sans-serif] font-normal leading-[1.5] relative shrink text-[14px] text-black whitespace-normal" style={{ fontVariationSettings: "'wdth' 100" }}>
        © 2026 AI Identity. All rights reserved.
      </p>
    </div>
  );
}

function SocialLinks() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Social Links">
      <Link14 />
      <Link15 />
      <Link16 />
      <Link17 />
      <Link18 />
    </div>
  );
}

function Column7() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full" data-name="Column">
      <p className="font-['Roboto:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-black w-full" style={{ fontVariationSettings: "'wdth' 100" }}>
        Social
      </p>
      <SocialLinks />
    </div>
  );
}

function Links() {
  return (
    <div className="content-stretch flex flex-col gap-[40px] items-start relative shrink-0 w-full" data-name="Links">
      <Column5 />
      <Column6 />
      <Column7 />
    </div>
  );
}

function Card() {
  return (
    <div className="bg-white relative shrink-0 w-full" data-name="Card">
      <div aria-hidden="true" className="absolute border border-black border-solid inset-0 pointer-events-none" />
      <div className="content-stretch flex flex-col gap-[48px] items-start p-[32px] relative w-full">
        <Newsletter />
        <Links />
      </div>
    </div>
  );
}

function FooterLinks2() {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-start relative shrink-0 underline" data-name="Footer Links">
      <p className="[text-decoration-skip-ink:none] decoration-solid relative shrink-0" style={{ fontVariationSettings: "'wdth' 100" }}>
        Terms of service
      </p>
      <p className="[text-decoration-skip-ink:none] decoration-solid relative shrink-0" style={{ fontVariationSettings: "'wdth' 100" }}>
        Cookie settings
      </p>
    </div>
  );
}

function Row3() {
  return (
    <div className="content-stretch flex flex-col font-['Roboto:Regular',sans-serif] font-normal gap-[32px] items-start leading-[1.5] relative shrink-0 text-[14px] text-black w-full whitespace-nowrap" data-name="Row">
      <FooterLinks2 />
      <p className="relative shrink-0" style={{ fontVariationSettings: "'wdth' 100" }}>
        Privacy policy
      </p>
    </div>
  );
}

function Credits() {
  return (
    <div className="content-stretch flex flex-col items-start pb-[16px] relative shrink-0 w-full" data-name="Credits">
      <Row3 />
    </div>
  );
}

function Component3() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[32px] items-start min-h-px min-w-px relative" data-name="Component">
      <Card />
      <Credits />
    </div>
  );
}

function Container5() {
  return (
    <div className="content-stretch flex items-start max-w-[1280px] relative shrink-0 w-full" data-name="Container">
      <Component3 />
    </div>
  );
}

function Footer() {
  return (
    <div className="bg-white relative shrink-0 w-full" data-name="Footer / 9 /">
      <div className="flex flex-col items-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-center px-[20px] py-[48px] relative w-full">
          <Container5 />
        </div>
      </div>
    </div>
  );
}

export default function SecurityMobile() {
  return (
    <div className="content-stretch flex flex-col items-start relative size-full" data-name="Security • Mobile">
      <Navbar />
      <Header />
      <Layout />
      <Layout1 />
      <Faq />
      <Cta />
      <Footer />
    </div>
  );
}
