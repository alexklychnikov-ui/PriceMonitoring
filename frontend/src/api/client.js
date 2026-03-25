import axios from "axios";
export const api = axios.create({
    baseURL: "/api",
});
export async function fetchOverview() {
    const { data } = await api.get("/analytics/overview");
    return data;
}
export async function fetchProducts() {
    const { data } = await api.get("/products");
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
