import axios from "axios";
import type { ParsingStatus, PriceHistory, Product, RuntimeSettings, Site } from "../types";

export const api = axios.create({
  baseURL: "/api",
});

const subscriptionKey = (import.meta.env.VITE_SUBSCRIPTION_WEB_KEY || "").trim();
if (subscriptionKey) {
  api.defaults.headers.common["X-Subscription-Key"] = subscriptionKey;
}

export async function fetchOverview(): Promise<Record<string, number>> {
  const { data } = await api.get("/analytics/overview");
  return data;
}

export async function fetchProducts(
  includeUnavailable = false,
): Promise<{ items: Product[]; total: number }> {
  const { data } = await api.get("/products", {
    params: { include_unavailable: includeUnavailable },
  });
  return data;
}

export async function fetchProduct(id: number): Promise<Product> {
  const { data } = await api.get(`/products/${id}`);
  return data;
}

export async function fetchProductHistory(id: number): Promise<PriceHistory[]> {
  const { data } = await api.get(`/products/${id}/history`);
  return data;
}

export async function fetchProductSubscription(productId: number): Promise<{ subscribed: boolean }> {
  const { data } = await api.get(`/products/${productId}/subscription`);
  return data;
}

export async function subscribeToProduct(productId: number): Promise<{ ok: boolean }> {
  const { data } = await api.post(`/products/${productId}/subscription`);
  return data;
}

export async function unsubscribeFromProduct(productId: number): Promise<{ ok: boolean }> {
  const { data } = await api.delete(`/products/${productId}/subscription`);
  return data;
}

export async function fetchPriceChanges(): Promise<Array<Record<string, unknown>>> {
  const { data } = await api.get("/analytics/price-changes");
  return data;
}

export async function fetchBestDeals(): Promise<Array<Record<string, unknown>>> {
  const { data } = await api.get("/analytics/best-deals");
  return data;
}

export async function fetchSitesSettings(): Promise<Site[]> {
  const { data } = await api.get("/settings/sites");
  return data;
}

export async function updateSiteStatus(siteId: number, isActive: boolean): Promise<{ ok: boolean; id: number; is_active: boolean }> {
  const { data } = await api.put(`/settings/sites/${siteId}`, { is_active: isActive });
  return data;
}

export async function updateSitesBulkStatus(
  items: Array<{ id: number; is_active: boolean }>,
): Promise<{ ok: boolean; updated: number; items: Array<{ id: number; is_active: boolean }> }> {
  const { data } = await api.put("/settings/sites", { items });
  return data;
}

export async function fetchRuntimeSettings(): Promise<RuntimeSettings> {
  const { data } = await api.get("/settings/runtime");
  return data;
}

export async function updateRuntimeSettings(payload: Partial<RuntimeSettings>): Promise<RuntimeSettings> {
  const { data } = await api.put("/settings/runtime", payload);
  return data;
}

export async function fetchParsingStatus(): Promise<ParsingStatus> {
  const { data } = await api.get("/settings/parsing-status");
  return data;
}

export async function triggerScrapeNow(): Promise<{ ok: boolean; sites_count: number; sites: string[]; task_id: string }> {
  const { data } = await api.post("/settings/scrape-now");
  return data;
}
