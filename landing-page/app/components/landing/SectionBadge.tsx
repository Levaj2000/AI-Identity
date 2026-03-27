interface SectionBadgeProps {
  label: string;
  icon?: React.ReactNode;
}

export function SectionBadge({ label, icon }: SectionBadgeProps) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 mb-4">
      {icon && <span className="text-[#F59E0B]">{icon}</span>}
      <span className="text-xs font-medium uppercase tracking-[0.2em] text-[#8B9BB4]">
        {label}
      </span>
    </div>
  );
}
