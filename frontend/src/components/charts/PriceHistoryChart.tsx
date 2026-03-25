import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = {
  date: string;
  price: number;
};

type Props = {
  data: Point[];
};

export function PriceHistoryChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data}>
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Area dataKey="price" stroke="#22c55e" fill="#22c55e33" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
