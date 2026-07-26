/** User-facing Chinese labels for lottery UI. */

export function lotteryLabel(lotteryType: string | null | undefined): string {
  const value = String(lotteryType || "").toLowerCase();
  if (value === "ssq") return "双色球";
  if (value === "dlt") return "大乐透";
  return lotteryType || "未知彩种";
}

export function aiStatusLabel(status: string | null | undefined): string {
  const value = String(status || "").toLowerCase();
  const map: Record<string, string> = {
    succeeded: "AI 已完成",
    failed: "AI 失败（已降级统计）",
    skipped: "未使用 AI",
    running: "AI 处理中",
    queued: "排队中",
    disabled: "AI 已关闭",
  };
  return map[value] || (status ? `AI：${status}` : "AI 未知");
}

export function translateTag(raw: string): string {
  const label = String(raw || "");
  if (label.startsWith("source:")) {
    const source = label.slice("source:".length);
    const sourceMap: Record<string, string> = {
      weighted: "加权抽样",
      uniform: "均匀随机",
      structure: "结构抽样",
      explore: "探索抽样",
      unknown: "未知来源",
    };
    return `来源：${sourceMap[source] || source}`;
  }
  if (label.startsWith("sum:")) return `和值：${label.slice(4)}`;
  if (label.startsWith("span:")) return `跨度：${label.slice(5)}`;
  if (label.startsWith("oe:")) return `奇偶：${label.slice(3)}`;
  if (label.startsWith("zone:")) return `区间：${label.slice(5)}`;
  return label;
}
