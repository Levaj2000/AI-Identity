import svgPaths from "./svg-engzlcpen2";
import imgIcon from "figma:asset/7866b7528c65cf3e718cdb157932316347355993.png";

export default function VariantShortcutThemedFalse({ className }: { className?: string }) {
  return (
    <div className={className || "relative rounded-[56px] size-[48px]"} data-name="Variant=Shortcut, Themed?=False">
      <div className="absolute inset-0 overflow-clip rounded-[56px]" data-name="Shortcut">
        <div className="absolute bg-[#fffbff] inset-[-25%]" data-name=".Launcher Shortcut Icon">
          <div className="absolute inset-[27.78%]" data-name="search">
            <div className="absolute inset-[12.5%_14.63%_14.63%_12.5%]" data-name="vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 23.32 23.32">
                <path clipRule="evenodd" d={svgPaths.p18891a72} fill="var(--fill-0, #A83159)" fillRule="evenodd" id="vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <div className="absolute bottom-0 right-0 size-[20px]" data-name="Launcher Icon">
        <div className="absolute inset-0 rounded-[99px]" data-name="Icon">
          <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none rounded-[99px] size-full" src={imgIcon} />
        </div>
      </div>
    </div>
  );
}
