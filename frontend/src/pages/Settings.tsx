import { useSitesSettings } from "../hooks/useSettings";

export function SettingsPage() {
  const { data, isLoading } = useSitesSettings();
  if (isLoading) {
    return <div className="card">Загрузка...</div>;
  }
  return (
    <div className="card">
      <h3>Настройки сайтов</h3>
      <table style={{ width: "100%" }}>
        <thead>
          <tr>
            <th align="left">Сайт</th>
            <th align="left">Активен</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((site) => (
            <tr key={site.id}>
              <td>{site.name}</td>
              <td>{site.is_active ? "Да" : "Нет"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
