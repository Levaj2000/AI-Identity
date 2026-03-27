import svgPaths from "../../imports/svg-pvrwh33c0c";
import imgPlaceholderImage from "figma:asset/b4d0118543bc011744949ebbf871f95430182503.png";
import imgPlaceholderImage1 from "figma:asset/f83aefda4fcaa0a98985f08523b8407a6849bf84.png";
import imgPlaceholderImage2 from "figma:asset/123598581007b9dfa52e07bb013d8c8f0bf3cf1b.png";
import { Link } from "react-router";

function Content1() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-center relative shrink-0 text-center w-full" data-name="Content">
      <p className="font-['Inter',sans-serif] font-bold leading-[1.2] not-italic relative shrink-0 text-white text-[56px] w-full">Identity for AI agents</p>
      <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[18px] text-gray-300 w-full">
        Give each AI agent its own API key, scoped permissions, and audit trail. The proxy gateway authenticates every request, enforces policies, and logs every decision.
      </p>
    </div>
  );
}

function Actions() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0" data-name="Actions">
      <a href="https://dashboard.ai-identity.co" className="bg-[#00ffc2] content-stretch flex items-center justify-center px-[24px] py-[12px] relative shrink-0 rounded-lg hover:bg-[#00e6ad] transition-colors cursor-pointer" data-name="Button">
        <p className="font-['Inter',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[#0a0a0b] text-[16px] whitespace-nowrap">
          Get started
        </p>
      </a>
      <Link to="/how-it-works" className="content-stretch flex items-center justify-center px-[24px] py-[12px] relative shrink-0 border border-[#00ffc2] rounded-lg hover:bg-[#00ffc2]/10 transition-colors cursor-pointer" data-name="Button">
        <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-[#00ffc2] whitespace-nowrap">
          Learn more
        </p>
      </Link>
    </div>
  );
}

function Column() {
  return (
    <div className="content-stretch flex flex-col gap-[32px] items-center max-w-[768px] relative shrink-0 w-full" data-name="Column">
      <Content1 />
      <Actions />
    </div>
  );
}

function Container() {
  return (
    <div className="content-stretch flex flex-col items-center max-w-[1280px] relative shrink-0 w-full" data-name="Container">
      <Column />
    </div>
  );
}

function Content() {
  return (
    <div className="relative shrink-0 w-full" data-name="Content">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col items-center px-[64px] py-[112px] relative w-full">
          <Container />
        </div>
      </div>
    </div>
  );
}

function Header1() {
  return (
    <div className="content-stretch flex flex-col items-center overflow-clip relative shrink-0 w-full" data-name="Header / 145 /">
      <Content />
      <div className="aspect-[1440/810] relative shrink-0 w-full" data-name="Placeholder Image">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full rounded-2xl opacity-50" src={imgPlaceholderImage} />
      </div>
    </div>
  );
}

function SectionInfo() {
  return (
    <div className="content-stretch flex font-['Inter',sans-serif] font-semibold gap-[24px] h-[64px] items-center leading-[1.5] relative shrink-0 text-[18px] text-[#00ffc2] w-full whitespace-nowrap" data-name="Section Info">
      <p className="relative shrink-0">01</p>
      <p className="relative shrink-0">Registration</p>
    </div>
  );
}

function TaglineWrapper() {
  return (
    <div className="content-stretch flex items-center relative shrink-0" data-name="Tagline Wrapper">
      <p className="font-['Inter',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-[#00ffc2] whitespace-nowrap">
        Initialize
      </p>
    </div>
  );
}

function Content4() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 text-white w-full" data-name="Content">
      <p className="font-['Inter',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[48px] w-full">
        Your agent requests an identity
      </p>
      <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[18px] text-gray-300 w-full">{`Register your agent and get a unique API key in one call. The key is hashed, shown once, and tied to your agent's lifecycle.`}</p>
    </div>
  );
}

function SectionTitle() {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-start relative shrink-0 w-full" data-name="Section Title">
      <TaglineWrapper />
      <Content4 />
    </div>
  );
}

function Actions1() {
  return (
    <div className="content-stretch flex gap-[24px] items-center relative shrink-0" data-name="Actions">
      <Link to="/how-it-works" className="relative shrink-0 border border-gray-600 rounded-lg px-[24px] py-[12px] hover:border-[#00ffc2] transition-colors cursor-pointer" data-name="Button">
        <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-white whitespace-nowrap">
          Explore
        </p>
      </Link>
      <div className="content-stretch flex gap-[8px] items-center justify-center overflow-clip relative shrink-0 cursor-pointer hover:text-[#00ffc2] transition-colors text-white" data-name="Button">
        <span className="sr-only">Navigate</span>
        <div className="overflow-clip relative shrink-0 size-[24px]" data-name="chevron_right">
          <div className="absolute inset-[25.72%_36.66%_25.88%_35.46%]" data-name="Vector">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6.69159 11.6166">
              <path d={svgPaths.p36daa800} fill="currentColor" id="Vector" stroke="currentColor" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Content3() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[32px] items-start min-h-px min-w-px relative" data-name="Content">
      <SectionTitle />
      <Actions1 />
    </div>
  );
}

function Content2() {
  return (
    <div className="content-stretch flex gap-[80px] items-center relative shrink-0 w-full" data-name="Content">
      <Content3 />
      <div className="aspect-[616/616] flex-[1_0_0] min-h-px min-w-px relative rounded-2xl overflow-hidden" data-name="Placeholder Image">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPlaceholderImage1} />
      </div>
    </div>
  );
}

function Container1() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[48px] items-start max-w-[1280px] min-h-px min-w-px pb-[112px] relative" data-name="Container">
      <SectionInfo />
      <Content2 />
    </div>
  );
}

function FeatureOne() {
  return (
    <div className="relative shrink-0 w-full bg-white/5 backdrop-blur-[20px] border border-white/10 rounded-3xl" data-name="Feature one">
      <div className="flex flex-row justify-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex items-start justify-center px-[64px] py-[56px] relative w-full">
          <Container1 />
        </div>
      </div>
    </div>
  );
}

function SectionInfo1() {
  return (
    <div className="content-stretch flex font-['Inter',sans-serif] font-semibold gap-[24px] h-[64px] items-center leading-[1.5] relative shrink-0 text-[18px] text-[#00ffc2] w-full whitespace-nowrap" data-name="Section Info">
      <p className="relative shrink-0">02</p>
      <p className="relative shrink-0">Verification</p>
    </div>
  );
}

function TaglineWrapper1() {
  return (
    <div className="content-stretch flex items-center relative shrink-0" data-name="Tagline Wrapper">
      <p className="font-['Inter',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-[#00ffc2] whitespace-nowrap">
        Authenticate
      </p>
    </div>
  );
}

function Content7() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 text-white w-full" data-name="Content">
      <p className="font-['Inter',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[48px] w-full">
        Every request is verified before execution
      </p>
      <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[18px] text-gray-300 w-full">
        The gateway intercepts calls, validates agent keys, and ensures only authorized operations proceed through your infrastructure.
      </p>
    </div>
  );
}

function SectionTitle1() {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-start relative shrink-0 w-full" data-name="Section Title">
      <TaglineWrapper1 />
      <Content7 />
    </div>
  );
}

function Actions2() {
  return (
    <div className="content-stretch flex gap-[24px] items-center relative shrink-0" data-name="Actions">
      <Link to="/how-it-works" className="relative shrink-0 border border-gray-600 rounded-lg px-[24px] py-[12px] hover:border-[#00ffc2] transition-colors cursor-pointer" data-name="Button">
        <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-white whitespace-nowrap">
          Explore
        </p>
      </Link>
      <div className="content-stretch flex gap-[8px] items-center justify-center overflow-clip relative shrink-0 cursor-pointer hover:text-[#00ffc2] transition-colors text-white" data-name="Button">
        <span className="sr-only">Navigate</span>
        <div className="overflow-clip relative shrink-0 size-[24px]" data-name="chevron_right">
          <div className="absolute inset-[25.72%_36.66%_25.88%_35.46%]" data-name="Vector">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6.69159 11.6166">
              <path d={svgPaths.p36daa800} fill="currentColor" id="Vector" stroke="currentColor" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Content6() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[32px] items-start min-h-px min-w-px relative" data-name="Content">
      <SectionTitle1 />
      <Actions2 />
    </div>
  );
}

function Content5() {
  return (
    <div className="content-stretch flex gap-[80px] items-center relative shrink-0 w-full" data-name="Content">
      <Content6 />
      <div className="aspect-[616/616] flex-[1_0_0] min-h-px min-w-px relative rounded-2xl overflow-hidden" data-name="Placeholder Image">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPlaceholderImage2} />
      </div>
    </div>
  );
}

function Container2() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[48px] items-start max-w-[1280px] min-h-px min-w-px pb-[112px] relative" data-name="Container">
      <SectionInfo1 />
      <Content5 />
    </div>
  );
}

function FeatureTwo() {
  return (
    <div className="relative shrink-0 w-full bg-white/5 backdrop-blur-[20px] border border-white/10 rounded-3xl" data-name="Feature two">
      <div className="flex flex-row justify-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex items-start justify-center px-[64px] py-[56px] relative w-full">
          <Container2 />
        </div>
      </div>
    </div>
  );
}

function SectionInfo2() {
  return (
    <div className="content-stretch flex font-['Inter',sans-serif] font-semibold gap-[24px] h-[64px] items-center leading-[1.5] relative shrink-0 text-[18px] text-[#00ffc2] w-full whitespace-nowrap" data-name="Section Info">
      <p className="relative shrink-0">03</p>
      <p className="relative shrink-0">Audit</p>
    </div>
  );
}

function TaglineWrapper2() {
  return (
    <div className="content-stretch flex items-center relative shrink-0" data-name="Tagline Wrapper">
      <p className="font-['Inter',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-[#00ffc2] whitespace-nowrap">
        Track
      </p>
    </div>
  );
}

function Content10() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 text-white w-full" data-name="Content">
      <p className="font-['Inter',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[48px] w-full">
        Every action is logged and immutable
      </p>
      <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[18px] text-gray-300 w-full">
        Complete audit trails capture identity usage, permissions granted, and all operations performed by your agents.
      </p>
    </div>
  );
}

function SectionTitle2() {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-start relative shrink-0 w-full" data-name="Section Title">
      <TaglineWrapper2 />
      <Content10 />
    </div>
  );
}

function Actions3() {
  return (
    <div className="content-stretch flex gap-[24px] items-center relative shrink-0" data-name="Actions">
      <Link to="/how-it-works" className="relative shrink-0 border border-gray-600 rounded-lg px-[24px] py-[12px] hover:border-[#00ffc2] transition-colors cursor-pointer" data-name="Button">
        <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-white whitespace-nowrap">
          Explore
        </p>
      </Link>
      <div className="content-stretch flex gap-[8px] items-center justify-center overflow-clip relative shrink-0 cursor-pointer hover:text-[#00ffc2] transition-colors text-white" data-name="Button">
        <span className="sr-only">Navigate</span>
        <div className="overflow-clip relative shrink-0 size-[24px]" data-name="chevron_right">
          <div className="absolute inset-[25.72%_36.66%_25.88%_35.46%]" data-name="Vector">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6.69159 11.6166">
              <path d={svgPaths.p36daa800} fill="currentColor" id="Vector" stroke="currentColor" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Content9() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[32px] items-start min-h-px min-w-px relative" data-name="Content">
      <SectionTitle2 />
      <Actions3 />
    </div>
  );
}

function Content8() {
  return (
    <div className="content-stretch flex gap-[80px] items-center relative shrink-0 w-full" data-name="Content">
      <Content9 />
      <div className="aspect-[616/616] flex-[1_0_0] min-h-px min-w-px relative rounded-2xl overflow-hidden" data-name="Placeholder Image">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPlaceholderImage1} />
      </div>
    </div>
  );
}

function Container3() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[48px] items-start max-w-[1280px] min-h-px min-w-px pb-[112px] relative" data-name="Container">
      <SectionInfo2 />
      <Content8 />
    </div>
  );
}

function FeatureThree() {
  return (
    <div className="relative shrink-0 w-full bg-white/5 backdrop-blur-[20px] border border-white/10 rounded-3xl" data-name="Feature three">
      <div className="flex flex-row justify-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex items-start justify-center px-[64px] py-[56px] relative w-full">
          <Container3 />
        </div>
      </div>
    </div>
  );
}

function HomeFeatureSection() {
  return (
    <div className="content-stretch flex flex-col items-center overflow-clip relative shrink-0 w-full gap-8" data-name="Layout / 356 /">
      <FeatureOne />
      <FeatureTwo />
      <FeatureThree />
    </div>
  );
}

function TaglineWrapper3() {
  return (
    <div className="content-stretch flex items-center relative shrink-0" data-name="Tagline Wrapper">
      <p className="font-['Inter',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[16px] text-[#00ffc2] text-center whitespace-nowrap">
        Security
      </p>
    </div>
  );
}

function Content11() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-center relative shrink-0 text-white text-center w-full" data-name="Content">
      <p className="font-['Inter',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[48px] w-full">
        Fail-closed by design
      </p>
      <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[18px] text-gray-300 w-full">
        Every safeguard defaults to denial. Your agents operate only within explicitly granted permissions, with no exceptions.
      </p>
    </div>
  );
}

function SectionTitle3() {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-center max-w-[768px] relative shrink-0 w-full" data-name="Section Title">
      <TaglineWrapper3 />
      <Content11 />
    </div>
  );
}

function Content13() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-center relative shrink-0 text-white text-center w-full" data-name="Content">
      <p className="font-['Inter',sans-serif] font-bold leading-[1.3] relative shrink-0 text-[32px] w-full">
        Zero-trust architecture
      </p>
      <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-gray-300 w-full">
        Every request is authenticated and authorized, regardless of source or context.
      </p>
    </div>
  );
}

function Column1() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[24px] items-center min-h-px min-w-px relative" data-name="Column">
      <div className="relative shrink-0 size-[48px]" data-name="architecture">
        <div className="absolute inset-[11.95%_26.68%_13.55%_26.68%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22.383 35.7591">
            <path d={svgPaths.p29daf300} fill="#00ffc2" id="Vector" />
          </svg>
        </div>
      </div>
      <Content13 />
    </div>
  );
}

function Content14() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-center relative shrink-0 text-white text-center w-full" data-name="Content">
      <p className="font-['Inter',sans-serif] font-bold leading-[1.3] relative shrink-0 text-[32px] w-full">
        Hashed key storage
      </p>
      <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-gray-300 w-full">
        Agent keys are SHA-256 hashed at rest and never returned after creation. You hold the key — we hold the hash.
      </p>
    </div>
  );
}

function Column2() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[24px] items-center min-h-px min-w-px relative" data-name="Column">
      <div className="relative shrink-0 size-[48px]" data-name="encrypted">
        <div className="absolute inset-[8.02%_16.02%_8.15%_16.04%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 32.61 40.236">
            <path d={svgPaths.pcc672c0} fill="#00ffc2" id="Vector" />
          </svg>
        </div>
      </div>
      <Content14 />
    </div>
  );
}

function Content15() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-center relative shrink-0 text-white text-center w-full" data-name="Content">
      <p className="font-['Inter',sans-serif] font-bold leading-[1.3] relative shrink-0 text-[32px] w-full">
        Immutable audit logs
      </p>
      <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-gray-300 w-full">
        All identity operations are recorded and cannot be altered or deleted after creation.
      </p>
    </div>
  );
}

function Column3() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[24px] items-center min-h-px min-w-px relative" data-name="Column">
      <div className="relative shrink-0 size-[48px]" data-name="identity_platform">
        <div className="absolute inset-[6.72%_11.85%_6.69%_11.88%]" data-name="Vector">
          <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 36.61 41.562">
            <path d={svgPaths.p778f400} fill="#00ffc2" id="Vector" />
          </svg>
        </div>
      </div>
      <Content15 />
    </div>
  );
}

function Row() {
  return (
    <div className="content-stretch flex gap-[48px] items-start relative shrink-0 w-full" data-name="Row">
      <Column1 />
      <Column2 />
      <Column3 />
    </div>
  );
}

function Content12() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full" data-name="Content">
      <Row />
    </div>
  );
}

function Actions4() {
  return (
    <div className="content-stretch flex gap-[24px] items-center relative shrink-0" data-name="Actions">
      <Link to="/security" className="relative shrink-0 border border-gray-600 rounded-lg px-[24px] py-[12px] hover:border-[#00ffc2] transition-colors cursor-pointer" data-name="Button">
        <p className="font-['Inter',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[16px] text-white whitespace-nowrap">
          Learn more
        </p>
      </Link>
      <div className="content-stretch flex gap-[8px] items-center justify-center overflow-clip relative shrink-0 cursor-pointer hover:text-[#00ffc2] transition-colors text-white" data-name="Button">
        <span className="sr-only">Navigate</span>
        <div className="overflow-clip relative shrink-0 size-[24px]" data-name="chevron_right">
          <div className="absolute inset-[25.72%_36.66%_25.88%_35.46%]" data-name="Vector">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6.69159 11.6166">
              <path d={svgPaths.p36daa800} fill="currentColor" id="Vector" stroke="currentColor" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Container4() {
  return (
    <div className="content-stretch flex flex-col gap-[80px] items-center max-w-[1280px] relative shrink-0 w-full" data-name="Container">
      <SectionTitle3 />
      <Content12 />
      <Actions4 />
    </div>
  );
}

function HomeSecuritySection() {
  return (
    <div className="relative shrink-0 w-full bg-white/5 backdrop-blur-[20px] border border-white/10 rounded-3xl" data-name="Layout / 237 /">
      <div className="flex flex-col items-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-center px-[64px] py-[112px] relative w-full">
          <Container4 />
        </div>
      </div>
    </div>
  );
}

export default function HomeDark() {
  return (
    <div className="size-full overflow-auto bg-[#0A0A0B]">
      <div className="min-h-full flex flex-col">
        <Header1 />
        <div className="px-[64px] py-8 flex flex-col gap-8">
          <HomeFeatureSection />
          <HomeSecuritySection />
        </div>
      </div>
    </div>
  );
}
