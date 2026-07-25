import type { RecommendationRun, RecommendationTicket } from "@/types/recommendations";

export function formatTicketLine(ticket: RecommendationTicket): string {
  const primary = (ticket.primary_numbers ?? [])
    .map((n) => String(n).padStart(2, "0"))
    .join(" ");
  const secondary = (ticket.secondary_numbers ?? [])
    .map((n) => String(n).padStart(2, "0"))
    .join(" ");
  return secondary ? `${primary} + ${secondary}` : primary;
}

export function formatRunTickets(run: RecommendationRun): string {
  const header = [
    `${(run.lottery_type || "").toUpperCase()} · 目标期 ${run.target_issue ?? "—"}`,
    run.seed != null ? `seed ${run.seed}` : null,
    run.ai_status ? `AI ${run.ai_status}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const lines = [...(run.tickets ?? [])]
    .sort((a, b) => a.rank - b.rank)
    .map((ticket) => `#${ticket.rank} ${formatTicketLine(ticket)}`);

  return [header, ...lines].join("\n");
}
