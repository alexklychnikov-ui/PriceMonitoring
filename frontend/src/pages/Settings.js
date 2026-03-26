import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { useParsingStatus, useRuntimeSettings, useSitesSettings, useTriggerScrapeNow, useUpdateRuntimeSettings, useUpdateSitesBulkStatus } from "../hooks/useSettings";
function SectionTitle({ children }) {
    return _jsx("h3", { style: { marginTop: 0 }, children: children });
}
const DEFAULT_RUNTIME = {
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
    const [localRuntime, setLocalRuntime] = useState(DEFAULT_RUNTIME);
    const [localSites, setLocalSites] = useState([]);
    const [notice, setNotice] = useState("");
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
        return _jsx("div", { className: "card", children: "\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430..." });
    }
    const saveRuntimeSettings = async () => {
        await updateRuntime.mutateAsync(localRuntime);
        setNotice("Настройки сохранены.");
    };
    const runScrapeNow = async () => {
        const result = await triggerScrapeNow.mutateAsync();
        setNotice(`Запущено задач парсинга: ${result.sites_count}`);
    };
    const setSiteActive = (siteId, isActive) => {
        setLocalSites((prev) => prev.map((site) => (site.id === siteId ? { ...site, is_active: isActive } : site)));
    };
    const formatDateTime = (value) => {
        if (!value) {
            return "—";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return "—";
        }
        return date.toLocaleString("ru-RU");
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
    return (_jsxs("div", { className: "grid", children: [_jsxs("div", { className: "card", children: [_jsx(SectionTitle, { children: "\u041E\u0431\u0449\u0438\u0435 \u043D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438 \u043F\u0430\u0440\u0441\u0438\u043D\u0433\u0430" }), _jsxs("label", { style: { display: "block", marginBottom: 8 }, children: [_jsx("input", { type: "checkbox", checked: localRuntime.parsing.winter, onChange: (event) => setLocalRuntime((prev) => ({ ...prev, parsing: { ...prev.parsing, winter: event.target.checked } })) }), " ", "\u0417\u0438\u043C\u0430"] }), _jsxs("div", { style: { marginLeft: 18, marginBottom: 8, opacity: localRuntime.parsing.winter ? 1 : 0.6 }, children: [_jsxs("label", { style: { display: "block", marginBottom: 6 }, children: [_jsx("input", { type: "checkbox", checked: localRuntime.parsing.winter_studded, disabled: !localRuntime.parsing.winter, onChange: (event) => setLocalRuntime((prev) => ({
                                            ...prev,
                                            parsing: { ...prev.parsing, winter_studded: event.target.checked },
                                        })) }), " ", "\u0428\u0438\u043F\u043E\u0432\u0430\u043D\u043D\u0430\u044F"] }), _jsxs("label", { style: { display: "block" }, children: [_jsx("input", { type: "checkbox", checked: localRuntime.parsing.winter_non_studded, disabled: !localRuntime.parsing.winter, onChange: (event) => setLocalRuntime((prev) => ({
                                            ...prev,
                                            parsing: { ...prev.parsing, winter_non_studded: event.target.checked },
                                        })) }), " ", "\u041D\u0435\u0448\u0438\u043F\u043E\u0432\u0430\u043D\u043D\u0430\u044F"] })] }), _jsxs("label", { style: { display: "block", marginBottom: 12 }, children: [_jsx("input", { type: "checkbox", checked: localRuntime.parsing.summer, onChange: (event) => setLocalRuntime((prev) => ({ ...prev, parsing: { ...prev.parsing, summer: event.target.checked } })) }), " ", "\u041B\u0435\u0442\u043E"] }), _jsxs("label", { style: { display: "block", marginBottom: 12 }, children: ["\u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0430 \u043F\u0435\u0440\u0438\u043E\u0434\u0438\u0447\u043D\u043E\u0441\u0442\u0438 \u043F\u0430\u0440\u0441\u0438\u043D\u0433\u0430 (\u0447\u0430\u0441\u044B)", _jsx("input", { type: "number", min: 1, max: 168, value: localRuntime.parsing.parse_interval_hours, onChange: (event) => setLocalRuntime((prev) => ({
                                    ...prev,
                                    parsing: {
                                        ...prev.parsing,
                                        parse_interval_hours: Number(event.target.value || 1),
                                    },
                                })), style: { display: "block", marginTop: 6, width: 140 } })] }), _jsxs("div", { style: { marginBottom: 10 }, children: ["\u0412\u0440\u0435\u043C\u044F \u0441\u043B\u0435\u0434\u0443\u044E\u0449\u0435\u0433\u043E \u043E\u0431\u043D\u043E\u0432\u043B\u0435\u043D\u0438\u044F: ", formatDateTime(parsingStatus?.next_update_at)] }), _jsxs("div", { style: { marginBottom: 12, opacity: 0.85 }, children: ["\u041F\u043E\u0441\u043B\u0435\u0434\u043D\u0438\u0439 \u0437\u0430\u043F\u0443\u0441\u043A: ", formatDateTime(parsingStatus?.last_started_at)] }), _jsx("button", { type: "button", onClick: runScrapeNow, disabled: triggerScrapeNow.isPending || (parsingStatus?.active_sites_count ?? 0) === 0, style: { marginRight: 8 }, children: triggerScrapeNow.isPending ? "Запуск..." : "Обновить сейчас" }), _jsx("button", { type: "button", onClick: saveRuntimeSettings, disabled: updateRuntime.isPending, children: updateRuntime.isPending ? "Сохранение..." : "Сохранить настройки парсинга" })] }), _jsxs("div", { className: "card", children: [_jsx(SectionTitle, { children: "\u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438 \u0441\u0430\u0439\u0442\u043E\u0432" }), _jsxs("table", { style: { width: "100%" }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { align: "left", children: "\u0421\u0430\u0439\u0442" }), _jsx("th", { align: "left", children: "\u0410\u043A\u0442\u0438\u0432\u0435\u043D" })] }) }), _jsx("tbody", { children: localSites.map((site) => (_jsxs("tr", { children: [_jsx("td", { children: site.name }), _jsx("td", { children: _jsxs("select", { value: site.is_active ? "yes" : "no", onChange: (event) => setSiteActive(site.id, event.target.value === "yes"), children: [_jsx("option", { value: "yes", children: "\u0414\u0430" }), _jsx("option", { value: "no", children: "\u041D\u0435\u0442" })] }) })] }, site.id))) })] }), _jsx("div", { style: { marginTop: 12 }, children: _jsx("button", { type: "button", onClick: saveSites, disabled: updateSitesBulkStatus.isPending, children: updateSitesBulkStatus.isPending ? "Сохранение..." : "Сохранить настройки сайтов" }) })] }), _jsxs("div", { className: "card", children: [_jsx(SectionTitle, { children: "\u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0430 \u0430\u043B\u0435\u0440\u0442\u043E\u0432" }), _jsx("p", { style: { marginTop: 0, opacity: 0.85 }, children: "\u041C\u0438\u043D\u0438\u043C\u0430\u043B\u044C\u043D\u044B\u0439 \u043D\u0430\u0431\u043E\u0440: \u0432\u043A\u043B\u044E\u0447\u0438\u0442\u044C \u0443\u0432\u0435\u0434\u043E\u043C\u043B\u0435\u043D\u0438\u044F, \u0432\u044B\u0431\u0440\u0430\u0442\u044C \u043A\u0430\u043A\u0438\u0435 \u0441\u043E\u0431\u044B\u0442\u0438\u044F \u043E\u0442\u043F\u0440\u0430\u0432\u043B\u044F\u0442\u044C \u0438 \u043F\u043E\u0440\u043E\u0433 \u0438\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u044F \u0446\u0435\u043D\u044B." }), _jsxs("label", { style: { display: "block", marginBottom: 10 }, children: [_jsx("input", { type: "checkbox", checked: localRuntime.alerts.enabled, onChange: (event) => setLocalRuntime((prev) => ({ ...prev, alerts: { ...prev.alerts, enabled: event.target.checked } })) }), " ", "\u0412\u043A\u043B\u044E\u0447\u0438\u0442\u044C \u0443\u0432\u0435\u0434\u043E\u043C\u043B\u0435\u043D\u0438\u044F"] }), _jsxs("label", { style: { display: "block", marginBottom: 10 }, children: [_jsx("input", { type: "checkbox", checked: localRuntime.alerts.send_price_drop, disabled: !localRuntime.alerts.enabled, onChange: (event) => setLocalRuntime((prev) => ({
                                    ...prev,
                                    alerts: { ...prev.alerts, send_price_drop: event.target.checked },
                                })) }), " ", "\u041E\u0442\u043F\u0440\u0430\u0432\u043B\u044F\u0442\u044C \u043F\u0440\u0438 \u0441\u043D\u0438\u0436\u0435\u043D\u0438\u0438 \u0446\u0435\u043D\u044B"] }), _jsxs("label", { style: { display: "block", marginBottom: 12 }, children: [_jsx("input", { type: "checkbox", checked: localRuntime.alerts.send_price_rise, disabled: !localRuntime.alerts.enabled, onChange: (event) => setLocalRuntime((prev) => ({
                                    ...prev,
                                    alerts: { ...prev.alerts, send_price_rise: event.target.checked },
                                })) }), " ", "\u041E\u0442\u043F\u0440\u0430\u0432\u043B\u044F\u0442\u044C \u043F\u0440\u0438 \u0440\u043E\u0441\u0442\u0435 \u0446\u0435\u043D\u044B"] }), _jsxs("label", { style: { display: "block", marginBottom: 12 }, children: ["\u041F\u043E\u0440\u043E\u0433 \u0438\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u044F \u0446\u0435\u043D\u044B (%)", _jsx("input", { type: "number", min: 0.1, max: 100, step: 0.1, disabled: !localRuntime.alerts.enabled, value: localRuntime.alerts.min_change_pct, onChange: (event) => setLocalRuntime((prev) => ({
                                    ...prev,
                                    alerts: { ...prev.alerts, min_change_pct: Number(event.target.value || 0.1) },
                                })), style: { display: "block", marginTop: 6, width: 140 } })] }), _jsx("button", { type: "button", onClick: saveRuntimeSettings, disabled: updateRuntime.isPending, children: updateRuntime.isPending ? "Сохранение..." : "Сохранить настройки алертов" })] }), notice && (_jsx("div", { className: "card", style: { gridColumn: "1 / -1", paddingTop: 10, paddingBottom: 10 }, children: notice }))] }));
}
