const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })
const inrPrecise = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 })
const num = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 6 })
const date = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
const dateTime = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" })

type Numeric = string | number | null | undefined

/** ₹2,63,088 — whole rupees for totals and cards. */
export const formatMoney = (v: Numeric) => (v == null ? "—" : inr.format(Number(v)))
/** ₹1,038.95 — paise for prices and per-row amounts. */
export const formatMoneyPrecise = (v: Numeric) => (v == null ? "—" : inrPrecise.format(Number(v)))
export const formatNumber = (v: Numeric) => (v == null ? "—" : num.format(Number(v)))
export const formatPct = (v: Numeric) => (v == null ? "—" : `${Number(v).toFixed(2)}%`)
/** Prefix gains with + so the sign, not just colour, carries the meaning. */
export const formatSigned = (formatted: string, v: Numeric) => (Number(v) > 0 ? `+${formatted}` : formatted)
export const formatDate = (v: string | null | undefined) => (v ? date.format(new Date(v)) : "—")
export const formatDateTime = (v: string) => dateTime.format(new Date(v))

const LABELS: Record<string, string> = {
  MUTUAL_FUND: "Mutual fund", GSEC: "G-Sec", ETF: "ETF", REIT: "REIT", HNI: "HNI",
  EMERGENCY_FUND: "Emergency fund", HOME_PURCHASE: "Home purchase", WEALTH_CREATION: "Wealth creation",
  RISK_PROFILES: "Risk profiles",
}
/** EQUITY -> "Equity", MUTUAL_FUND -> "Mutual fund". */
export function humanize(value: string) {
  const key = value.toUpperCase()
  if (LABELS[key]) return LABELS[key]
  const words = value.replaceAll("_", " ").toLowerCase()
  return words.charAt(0).toUpperCase() + words.slice(1)
}
