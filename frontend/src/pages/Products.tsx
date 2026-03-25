import { useNavigate } from "react-router-dom";
import { useProducts } from "../hooks/useProducts";

export function ProductsPage() {
  const { data, isLoading } = useProducts();
  const navigate = useNavigate();

  if (isLoading) {
    return <div className="card">Загрузка...</div>;
  }

  return (
    <div className="card">
      <h3>Каталог товаров</h3>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th align="left">Название</th>
            <th align="left">Бренд</th>
            <th align="left">Размер</th>
            <th align="left">Радиус</th>
            <th align="left">Цена</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((row) => (
            <tr key={row.id} onClick={() => navigate(`/products/${row.id}`)} style={{ cursor: "pointer" }}>
              <td>{row.name}</td>
              <td>{row.brand}</td>
              <td>{row.tire_size}</td>
              <td>{row.radius}</td>
              <td>{row.current_price ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
