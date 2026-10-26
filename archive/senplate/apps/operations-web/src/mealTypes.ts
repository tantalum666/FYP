export type NutrientValues = Record<string, number | null>;
export type FoodReference = {
  id: string;
  slug: string;
  name_en: string;
  name_zh: string;
  food_group: string;
  cooked_state: string;
  notes_en: string;
  notes_zh: string;
  source: string;
  source_id: string | null;
  source_description: string;
  source_type: string;
  source_url: string | null;
  published_at: string | null;
  data_version: string;
  per_100_g: Record<string, string | null>;
};
export type PairRequest = {
  id: string;
  state: string;
  check_code: string;
  expires_at: string;
  meal_id: string | null;
  applicant_name?: string;
};
export type Meal = {
  id: string;
  run_id: string;
  workspace_id: string;
  mode: string;
  state: string;
  version: number;
  sample_code: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  data_origin: string;
  provided_g: number;
  remaining_g: number | null;
  remaining_reason: string | null;
  remaining_comparable: boolean;
  current: {
    net_g: number | null;
    last_valid_g: number | null;
    observation_id: string | null;
    observed_at: string | null;
    last_valid_at: string | null;
    connectivity: string;
    freshness: string;
    measurement_status: string;
    snapshot_version: number;
  } | null;
  prepared: {
    reference: FoodReference;
    baseline_g: number;
    candidate_g: number | null;
    validation_error: string | null;
  } | null;
  portions: {
    id: string;
    amount_g: number;
    reference: FoodReference;
    reference_id: string;
    entry_source: string;
    version: number;
    at: string;
  }[];
  nutrition: {
    status: string;
    total: NutrientValues;
    known_subtotal: NutrientValues;
    covered_g: Record<string, number>;
  };
  food_groups_g: Record<string, number>;
  plan_comparison: null | {
    status: string;
    plan: {
      name_en: string;
      name_zh: string;
      review_status: string;
      scope_en: string;
      scope_zh: string;
    };
    groups: {
      group: string;
      target_g: number;
      recorded_g: number;
      difference_g: number | null;
    }[];
  };
  history: { id: string; action: string; at: string; note: string }[];
  pairing?: { code: string | null; expires_at: string | null } | null;
  pair_request?: PairRequest | null;
};
export type StationConsole = {
  workspace_id: string;
  workspace_name: string;
  run_id: string | null;
  mode: string | null;
  data_origin: string | null;
  development: boolean;
  meal: Meal | null;
};
export type SampleReport = {
  items: Meal[];
  scope: string;
  data_origin: string;
  summary: {
    completed_samples: number;
    provided_g: number;
    remaining_observed_g: number | null;
    samples_with_remaining: number;
    samples_without_remaining: number;
  };
};
