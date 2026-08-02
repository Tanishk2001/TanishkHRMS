import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";

export default function DashCard({
  icon: Icon,
  eyebrow,
  title,
  children,
  footer,
}: {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="bg-surface border border-border rounded-xl p-5 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center">
          <Icon size={15} className="text-accent" />
        </div>
        <span className="text-[10px] uppercase tracking-widest text-muted font-mono">{eyebrow}</span>
      </div>
      <h3 className="font-display font-semibold text-[15px] mb-2">{title}</h3>
      <div className="flex-1 text-sm text-muted">{children}</div>
      {footer && <div className="mt-4 pt-4 border-t border-border">{footer}</div>}
    </div>
  );
}
