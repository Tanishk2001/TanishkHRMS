import { PolicySource } from "@/lib/api";

export default function SourceList({ sources }: { sources: PolicySource[] }) {
  if (!sources.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {sources.map((s, i) => (
        <span
          key={`${s.title}-${i}`}
          className="text-xs px-2 py-1 rounded-full bg-accent/10 text-accent border border-accent/25"
          title={s.filename ?? undefined}
        >
          {s.title} · {s.category}
        </span>
      ))}
    </div>
  );
}
