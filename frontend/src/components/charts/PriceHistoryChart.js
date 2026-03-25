import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
export function PriceHistoryChart({ data }) {
    return (_jsx(ResponsiveContainer, { width: "100%", height: 220, children: _jsxs(AreaChart, { data: data, children: [_jsx(XAxis, { dataKey: "date" }), _jsx(YAxis, {}), _jsx(Tooltip, {}), _jsx(Area, { dataKey: "price", stroke: "#22c55e", fill: "#22c55e33" })] }) }));
}
