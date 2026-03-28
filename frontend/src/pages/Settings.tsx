import { useEffect, useState } from "react";
import type { RuntimeSettings, Site } from "../types";
import { useParsingStatus, useRuntimeSettings, useSitesSettings, useTriggerScrapeNow, useUpdateRuntimeSettings, useUpdateSitesBulkStatus } from "../hooks/useSettings";

function SectionTitle({ children }: { children: string }) {
  return <h3 style={{ marginTop: 0 }}>{children}</h3>;
}

const DEFAULT_RUNTIME: RuntimeSettings = {
  parsing: {
    winter: true,
    winter_studded: true,
    winter_non_studded: true,
    summer: true,
    parse_interval_hours: 6,
  },
  alerts: {
    enabled: true,
    min_change_pct: 5,
    send_price_drop: true,
    send_price_rise: true,
  },
};

export function SettingsPage() {
  const { data: sites, isLoading: isSitesLoading } = useSitesSettings();
  const { data: runtime, isLoading: isRuntimeLoading } = useRuntimeSettings();
  const { data: parsingStatus } = useParsingStatus();
  const updateSitesBulkStatus = useUpdateSitesBulkStatus();
  const updateRuntime = useUpdateRuntimeSettings();
  const triggerScrapeNow = useTriggerScrapeNow();

  const [localRuntime, setLocalRuntime] = useState<RuntimeSettings>(DEFAULT_RUNTIME);
  const [localSites, setLocalSites] = useState<Site[]>([]);
  const [notice, setNotice] = useState<string>("");

  useEffect(() => {
    if (runtime) {
      setLocalRuntime(runtime);
    }
  }, [runtime]);

  useEffect(() => {
    if (sites) {
      setLocalSites(sites);
    }
  }, [sites]);

  if (isSitesLoading || isRuntimeLoading) {
    return <div className="card">Загрузка...</div>;
  }

  const saveRuntimeSettings = async () => {
    await updateRuntime.mutateAsync(localRuntime);
    setNotice("Настройки сохранены.");
  };

  const runScrapeNow = async () => {
    const result = await triggerScrapeNow.mutateAsync();
    setNotice(`Запущено задач парсинга: ${result.sites_count}`);
  };

  const setSiteActive = (siteId: number, isActive: boolean) => {
    setLocalSites((prev) => prev.map((site) => (site.id === siteId ? { ...site, is_active: isActive } : site)));
  };

  const formatDateTime = (value?: string | null) => {
    if (!value) {
      return "—";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "—";
    }
    return date.toLocaleString("ru-RU", { timeZone: "Asia/Irkutsk" });
  };

  const saveSites = async () => {
    const changed = localSites
      .filter((site) => {
        const original = sites?.find((item) => item.id === site.id);
        return !!original && original.is_active !== site.is_active;
      })
      .map((site) => ({ id: site.id, is_active: site.is_active }));

    if (changed.length === 0) {
      setNotice("Изменений по сайтам нет.");
      return;
    }

    await updateSitesBulkStatus.mutateAsync(changed);
    setNotice("Настройки сайтов сохранены.");
  };

  return (
    <div className="grid">
      <div className="card">
        <SectionTitle>Общие настройки парсинга</SectionTitle>
        <label style={{ display: "block", marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={localRuntime.parsing.winter}
            onChange={(event) =>
              setLocalRuntime((prev) => ({ ...prev, parsing: { ...prev.parsing, winter: event.target.checked } }))
            }
          />{" "}
          Зима
        </label>
        <div style={{ marginLeft: 18, marginBottom: 8, opacity: localRuntime.parsing.winter ? 1 : 0.6 }}>
          <label style={{ display: "block", marginBottom: 6 }}>
            <input
              type="checkbox"
              checked={localRuntime.parsing.winter_studded}
              disabled={!localRuntime.parsing.winter}
              onChange={(event) =>
                setLocalRuntime((prev) => ({
                  ...prev,
                  parsing: { ...prev.parsing, winter_studded: event.target.checked },
                }))
              }
            />{" "}
            Шипованная
          </label>
          <label style={{ display: "block" }}>
            <input
              type="checkbox"
              checked={localRuntime.parsing.winter_non_studded}
              disabled={!localRuntime.parsing.winter}
              onChange={(event) =>
                setLocalRuntime((prev) => ({
                  ...prev,
                  parsing: { ...prev.parsing, winter_non_studded: event.target.checked },
                }))
              }
            />{" "}
            Нешипованная
          </label>
        </div>
        <label style={{ display: "block", marginBottom: 12 }}>
          <input
            type="checkbox"
            checked={localRuntime.parsing.summer}
            onChange={(event) =>
              setLocalRuntime((prev) => ({ ...prev, parsing: { ...prev.parsing, summer: event.target.checked } }))
            }
          />{" "}
          Лето
        </label>
        <label style={{ display: "block", marginBottom: 12 }}>
          Настройка периодичности парсинга (часы)
          <input
            type="number"
            min={1}
            max={168}
            value={localRuntime.parsing.parse_interval_hours}
            onChange={(event) =>
              setLocalRuntime((prev) => ({
                ...prev,
                parsing: {
                  ...prev.parsing,
                  parse_interval_hours: Number(event.target.value || 1),
                },
              }))
            }
            style={{ display: "block", marginTop: 6, width: 140 }}
          />
        </label>
        <div style={{ marginBottom: 10 }}>Время следующего обновления (Иркутск): {formatDateTime(parsingStatus?.next_update_at)}</div>
        <div style={{ marginBottom: 12, opacity: 0.85 }}>Последний запуск (Иркутск): {formatDateTime(parsingStatus?.last_started_at)}</div>
        <button type="button" onClick={runScrapeNow} disabled={triggerScrapeNow.isPending || (parsingStatus?.active_sites_count ?? 0) === 0} style={{ marginRight: 8 }}>
          {triggerScrapeNow.isPending ? "Запуск..." : "Обновить сейчас"}
        </button>
        <button type="button" onClick={saveRuntimeSettings} disabled={updateRuntime.isPending}>
          {updateRuntime.isPending ? "Сохранение..." : "Сохранить настройки парсинга"}
        </button>
      </div>

      <div className="card">
        <SectionTitle>Настройки сайтов</SectionTitle>
        <table style={{ width: "100%" }}>
          <thead>
            <tr>
              <th align="left">Сайт</th>
              <th align="left">Активен</th>
            </tr>
          </thead>
          <tbody>
            {localSites.map((site) => (
              <tr key={site.id}>
                <td>{site.name}</td>
                <td>
                  <select value={site.is_active ? "yes" : "no"} onChange={(event) => setSiteActive(site.id, event.target.value === "yes")}>
                    <option value="yes">Да</option>
                    <option value="no">Нет</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: 12 }}>
          <button type="button" onClick={saveSites} disabled={updateSitesBulkStatus.isPending}>
            {updateSitesBulkStatus.isPending ? "Сохранение..." : "Сохранить настройки сайтов"}
          </button>
        </div>
      </div>

      <div className="card">
        <SectionTitle>Настройка алертов</SectionTitle>
        <p style={{ marginTop: 0, opacity: 0.85 }}>
          Минимальный набор: включить уведомления, выбрать какие события отправлять и порог изменения цены.
        </p>
        <label style={{ display: "block", marginBottom: 10 }}>
          <input
            type="checkbox"
            checked={localRuntime.alerts.enabled}
            onChange={(event) =>
              setLocalRuntime((prev) => ({ ...prev, alerts: { ...prev.alerts, enabled: event.target.checked } }))
            }
          />{" "}
          Включить уведомления
        </label>
        <label style={{ display: "block", marginBottom: 10 }}>
          <input
            type="checkbox"
            checked={localRuntime.alerts.send_price_drop}
            disabled={!localRuntime.alerts.enabled}
            onChange={(event) =>
              setLocalRuntime((prev) => ({
                ...prev,
                alerts: { ...prev.alerts, send_price_drop: event.target.checked },
              }))
            }
          />{" "}
          Отправлять при снижении цены
        </label>
        <label style={{ display: "block", marginBottom: 12 }}>
          <input
            type="checkbox"
            checked={localRuntime.alerts.send_price_rise}
            disabled={!localRuntime.alerts.enabled}
            onChange={(event) =>
              setLocalRuntime((prev) => ({
                ...prev,
                alerts: { ...prev.alerts, send_price_rise: event.target.checked },
              }))
            }
          />{" "}
          Отправлять при росте цены
        </label>
        <label style={{ display: "block", marginBottom: 12 }}>
          Порог изменения цены (%)
          <input
            type="number"
            min={0.1}
            max={100}
            step={0.1}
            disabled={!localRuntime.alerts.enabled}
            value={localRuntime.alerts.min_change_pct}
            onChange={(event) =>
              setLocalRuntime((prev) => ({
                ...prev,
                alerts: { ...prev.alerts, min_change_pct: Number(event.target.value || 0.1) },
              }))
            }
            style={{ display: "block", marginTop: 6, width: 140 }}
          />
        </label>
        <button type="button" onClick={saveRuntimeSettings} disabled={updateRuntime.isPending}>
          {updateRuntime.isPending ? "Сохранение..." : "Сохранить настройки алертов"}
        </button>
      </div>

      {notice && (
        <div className="card" style={{ gridColumn: "1 / -1", paddingTop: 10, paddingBottom: 10 }}>
          {notice}
        </div>
      )}
    </div>
  );
}
