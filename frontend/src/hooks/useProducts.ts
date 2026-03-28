import { useQuery } from "@tanstack/react-query";
import { fetchProduct, fetchProductHistory, fetchProducts } from "../api/client";

export function useProducts(includeUnavailable = false) {
  return useQuery({
    queryKey: ["products", { includeUnavailable }],
    queryFn: () => fetchProducts(includeUnavailable),
  });
}

export function useProduct(id: number) {
  return useQuery({
    queryKey: ["product", id],
    queryFn: () => fetchProduct(id),
    enabled: Number.isFinite(id),
  });
}

export function useProductHistory(id: number) {
  return useQuery({
    queryKey: ["product-history", id],
    queryFn: () => fetchProductHistory(id),
    enabled: Number.isFinite(id),
  });
}
