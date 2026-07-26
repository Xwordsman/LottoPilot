import type { RecommendationRun } from "@/types/recommendations";
import { lotteryLabel } from "@/lib/labels";

export type RunTitleMeta = {
  generationIndex: number;
  generationTotal: number;
};

/** Build per-run generation ordinals within the same lottery + target issue. */
export function buildRunTitleMetaMap(runs: RecommendationRun[]): Record<string, RunTitleMeta> {
  const groups = new Map<string, RecommendationRun[]>();
  for (const run of runs) {
    const key = `${run.lottery_type}::${run.target_issue ?? ""}`;
    const list = groups.get(key) ?? [];
    list.push(run);
    groups.set(key, list);
  }

  const map: Record<string, RunTitleMeta> = {};
  for (const list of groups.values()) {
    const sorted = [...list].sort((a, b) => {
      const ta = Date.parse(a.created_at || "") || 0;
      const tb = Date.parse(b.created_at || "") || 0;
      if (ta !== tb) return ta - tb;
      return String(a.id).localeCompare(String(b.id));
    });
    sorted.forEach((run, idx) => {
      map[run.id] = {
        generationIndex: idx + 1,
        generationTotal: sorted.length,
      };
    });
  }
  return map;
}

export function formatRunCreatedAt(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  return `${mm}-${dd} ${hh}:${mi}`;
}

export function formatRunTitle(
  run: RecommendationRun,
  meta?: RunTitleMeta | null,
): string {
  const parts = [`${lotteryLabel(run.lottery_type)} · 目标期 ${run.target_issue ?? "—"}`];
  if (meta) {
    parts.push(`第${meta.generationIndex}次`);
  } else {
    parts.push("本次");
  }
  const when = formatRunCreatedAt(run.created_at);
  if (when) parts.push(when);
  return parts.join(` · `);
}
