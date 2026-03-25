import axios from "axios";
import type { PriceHistory, Product, Site } from "../types";

export const api = axios.create({
  baseURL: "/api",
});

export async function fetchOverview(): Promise<Record<string, number>> {
  const { data } = await api.get("/analytics/overview");
  return data;
}

export async function fetchProducts(): Promise<{ items: Product[]; total: number }> {
  const { data } = await api.get("/products");
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
