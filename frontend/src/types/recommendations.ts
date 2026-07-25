export type RecommendationTicket = {
  id: string;
  rank: number;
  primary_numbers: number[];
  secondary_numbers: number[];
  statistical_score: number;
  ai_score: number | null;
  final_score: number;
  feature_summary: Record<string, unknown>;
  tags: Record<string, unknown>;
  explanation: string | null;
  primary_hits?: number | null;
  secondary_hits?: number | null;
  prize_level?: string | null;
};

export type RecommendationRun = {
  id: string;
  job_id: string;
  lottery_type: string;
  target_issue: string | null;
  strategy_profile_id: string;
  data_cutoff_issue: string | null;
  data_snapshot_hash: string | null;
  seed: number | null;
  candidate_count: number;
  ai_status: string;
  ai_provider?: string | null;
  ai_model?: string | null;
  status: string;
  evaluation?: {
    draw_issue?: string | null;
    best_rank?: number | null;
    best_primary_hits?: number | null;
    best_secondary_hits?: number | null;
    any_prize?: boolean;
    prize_rule_version?: string | null;
  } | null;
  metrics: Record<string, unknown>;
  created_at: string;
  finished_at: string | null;
  tickets: RecommendationTicket[];
};

export type RecommendationList = {
  items: RecommendationRun[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type BacktestRun = {
  id: string;
  job_id: string;
  lottery_type: string;
  strategy_profile_id: string;
  start_issue: string;
  end_issue: string;
  seed: number | null;
  baseline_trials: number;
  status: string;
  summary: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type BacktestList = {
  items: BacktestRun[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type AIConfig = {
  id: string;
  name: string;
  provider: string;
  base_url: string;
  model: string;
  has_api_key: boolean;
  api_key_masked: string;
  timeout_seconds: number;
  max_tokens: number;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};
