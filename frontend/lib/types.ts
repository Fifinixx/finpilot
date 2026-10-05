// Shapes returned by the Django API. Money and quantities arrive as decimal
// strings so no precision is lost in transit; format them only for display.

export type Paginated<T> = {
  count: number
  page: number
  page_size: number
  total_pages: number
  results: T[]
}

export type KycStatus = "VERIFIED" | "PENDING" | "REVIEW"
export type Segment = "Mass" | "Affluent" | "HNI"

export type CustomerListItem = {
  id: string
  full_name: string
  email: string
  city: string
  state: string
  kyc_status: KycStatus
  segment: Segment
  account_count: number
}

export type RiskProfile = {
  risk_score: number
  risk_level: "Conservative" | "Moderate" | "Growth" | "Aggressive"
  assessed_at: string
  horizon_years: number
  liquidity_need: "LOW" | "MEDIUM" | "HIGH"
}

export type CustomerDetail = CustomerListItem & {
  phone: string
  date_of_birth: string
  onboarded_at: string
  latest_risk_profile: RiskProfile | null
}

type MoneyTotals = {
  market_value: string
  cost_basis: string
  unrealised_gain: string
  unrealised_gain_pct: string | null
}

export type AssetClass = "EQUITY" | "ETF" | "MUTUAL_FUND" | "BOND" | "REIT" | "GSEC"

export type PortfolioAccount = MoneyTotals & {
  account_id: string
  account_type: "BROKERAGE" | "MUTUAL_FUND" | "RETIREMENT"
  provider: string
  status: "ACTIVE" | "DORMANT" | "CLOSED"
  opened_at: string
  base_currency: string
}

export type Position = MoneyTotals & {
  account_id: string
  instrument_id: string
  symbol: string
  name: string
  asset_class: AssetClass
  quantity: string
  avg_cost: string
  last_price: string
  price_as_of: string
}

export type Portfolio = {
  snapshot_date: string | null
  price_as_of: string | null
  prices_mixed_dates: boolean
  totals: MoneyTotals & { position_count: number }
  accounts: PortfolioAccount[]
  allocation: { asset_class: AssetClass; market_value: string; weight_pct: string }[]
  positions: Position[]
}

export type Goal = {
  id: string
  goal_type: string
  name: string
  target_amount: string
  current_funded_amount: string
  funded_pct: number
  target_date: string
  priority: "LOW" | "MEDIUM" | "HIGH"
  is_overdue: boolean
  is_overfunded: boolean
}

export type GoalList = {
  summary: {
    goal_count: number
    total_target: string
    total_funded: string
    funded_pct: string | null
    flagged_count: number
  }
  results: Goal[]
}

export type TransactionType = "BUY" | "SELL" | "DIVIDEND" | "FEE"
export type TransactionStatus = "SETTLED" | "PENDING" | "REVERSED"

export type Transaction = {
  id: string
  account_id: string
  instrument_id: string
  symbol: string
  instrument_name: string
  transaction_type: TransactionType
  trade_date: string
  quantity: string
  price: string
  amount: string
  status: TransactionStatus
}

export type ImportEntity =
  | "customers" | "accounts" | "instruments" | "holdings" | "transactions" | "goals" | "risk_profiles"

export type ImportRejection = {
  row_number: number
  errors: { field: string; message: string }[]
  raw: Record<string, string>
}

export type ImportBatch = {
  id: number
  entity: ImportEntity
  file_name: string
  status: "COMPLETED" | "FAILED"
  total_rows: number
  imported_count: number
  duplicate_count: number
  rejected_count: number
  error: string
  created_by: string | null
  created_at: string
}

export type ImportBatchDetail = ImportBatch & { rejections: ImportRejection[] }

export type ReconciliationException = {
  exception_type: string
  entity: string
  entity_id: string
  customer_id: string | null
  detail: string
}

export type DataQualityPage = Paginated<ReconciliationException> & {
  summary: { exception_type: string; count: number }[]
}
