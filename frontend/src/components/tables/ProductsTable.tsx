import type { Product } from "../../types";

type Props = {
  items: Product[];
};

export function ProductsTable({ items }: Props) {
  return (
    <table style={{ width: "100%" }}>
      <thead>
        <tr>
          <th align="left">Название</th>
          <th align="left">Цена</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id}>
            <td>{item.name}</td>
            <td>{item.current_price ?? "-"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
