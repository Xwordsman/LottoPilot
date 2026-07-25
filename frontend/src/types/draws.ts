export type LotteryType = "ssq" | "dlt";

export type DrawPublic = {
  id: string;
  lottery_type: LotteryType;
  issue: string;
  draw_date: string;
  primary_numbers: number[];
  secondary_numbers: number[];
  source: string;
  source_checksum: string | null;
  created_at: string;
  updated_at: string;
};

export type DrawListData = {
  items: DrawPublic[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type LatestDrawsData = {
  ssq: DrawPublic | null;
  dlt: DrawPublic | null;
};

export type SyncAcceptedData = {
  job_id: string;
  run_id: string;
  lottery_type: LotteryType;
  mode: "incremental" | "full";
  status: string;
};

export type IngestionRunPublic = {
  id: string;
  job_id: string | null;
  source_name: string;
  lottery_type: string;
  mode: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  pages_processed: number;
  records_seen: number;
  inserted_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
  cursor: string | null;
  error_summary: string | null;
};

export type IngestionRunListData = {
  items: IngestionRunPublic[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};
export type ImportPreviewRow = {
  row_number: number;
  lottery_type: string | null;
  issue: string | null;
  draw_date: string | null;
  primary_numbers: number[] | null;
  secondary_numbers: number[] | null;
  valid: boolean;
  errors: string[];
};

export type ImportPreviewData = {
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  rows: ImportPreviewRow[];
};

export type ImportCommitData = {
  inserted_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
};
