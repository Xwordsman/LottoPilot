import { Card } from "@/components/ui/Card";

export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <Card>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-slate-400">{description}</p>
      <p className="mt-4 text-sm text-slate-500">该模块会在后续 Phase 按规格实现。</p>
    </Card>
  );
}
