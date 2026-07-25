export type AnalyticsOverview = {
  lottery_type: "ssq" | "dlt";
  metrics: {
    total_draws: number;
    latest_issue: string | null;
    latest_draw_date: string | null;
    avg_sum: number | null;
    avg_span: number | null;
  };
  hot_cold: {
    window: number;
    hot: Array<{ number: number; count: number; ratio: number }>;
    cold: Array<{ number: number; count: number; ratio: number }>;
  };
  frequency_primary: Array<{ number: number; count: number; ratio: number }>;
  missing_primary: Array<{ number: number; missing: number; last_issue: string | null }>;
  sum_span: Array<{
    issue: string;
    draw_date: string;
    sum: number;
    span: number;
    odd: number;
    even: number;
    odd_even: string;
  }>;
  zones: Array<{
    issue: string;
    draw_date: string;
    zone_low: number;
    zone_mid: number;
    zone_high: number;
    pattern: string;
  }>;
  cooccurrence: Array<{ a: number; b: number; count: number }>;
};
