import { useQuery } from "@tanstack/react-query";
import { fetchBestDeals, fetchOverview, fetchPriceChanges } from "../api/client";

export function useOverview() {
  return useQuery({ queryKey: ["overview"], queryFn: fetchOverview });
}

export function usePriceChanges() {
  return useQuery({ queryKey: ["price-changes"], queryFn: fetchPriceChanges });
}

export function useBestDeals() {
  return useQuery({ queryKey: ["best-deals"], queryFn: fetchBestDeals });
}
