export default function RiskBadge({ value }: { value: string }) {
  return <span className={`badge ${value}`}>{value.toUpperCase()}</span>
}
