type Props = {
  title: string;
  value: string | number;
};

export function StatCard({ title, value }: Props) {
  return (
    <div className="card">
      <div>{title}</div>
      <strong>{value}</strong>
    </div>
  );
}
