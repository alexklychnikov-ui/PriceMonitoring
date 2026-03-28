import axios from "axios";
export const api = axios.create({
    baseURL: "/api",
});
const subscriptionKey = (import.meta.env.VITE_SUBSCRIPTION_WEB_KEY || "").trim();
if (subscriptionKey) {
    api.defaults.headers.common["X-Subscription-Key"] = subscriptionKey;
}
export async function fetchOverview() {
    const { data } = await api.get("/analytics/overview");
    return data;
}
export async function fetchProducts(includeUnavailable = false) {
    const { data } = await api.get("/products", {
        params: { include_unavailable: includeUnavailable },
    });
    return data;
}
export async function fetchProduct(id) {
    const { data } = await api.get(`/products/${id}`);
    return data;
}
export async function fetchProductHistory(id) {
    const { data } = await api.get(`/products/${id}/history`);
    return data;
}
export async function fetchProductSubscription(productId) {
    const { data } = await api.get(`/products/${productId}/subscription`);
    return data;
}
export async function subscribeToProduct(productId) {
    const { data } = await api.post(`/products/${productId}/subscription`);
    return data;
}
export async function unsubscribeFromProduct(productId) {
    const { data } = await api.delete(`/products/${productId}/subscription`);
    return data;
}
export async function fetchPriceChanges() {
    const { data } = await api.get("/analytics/price-changes");
    return data;
}
export async function fetchBestDeals() {
    const { data } = await api.get("/analytics/best-deals");
    return data;
}
export async function fetchSitesSettings() {
    const { data } = await api.get("/settings/sites");
    return data;
}
export async function updateSiteStatus(siteId, isActive) {
    const { data } = await api.put(`/settings/sites/${siteId}`, { is_active: isActive });
    return data;
}
export async function updateSitesBulkStatus(items) {
    const { data } = await api.put("/settings/sites", { items });
    return data;
}
export async function fetchRuntimeSettings() {
    const { data } = await api.get("/settings/runtime");
    return data;
}
export async function updateRuntimeSettings(payload) {
    const { data } = await api.put("/settings/runtime", payload);
    return data;
}
export async function fetchParsingStatus() {
    const { data } = await api.get("/settings/parsing-status");
    return data;
}
export async function triggerScrapeNow() {
    const { data } = await api.post("/settings/scrape-now");
    return data;
}
