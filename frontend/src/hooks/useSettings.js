import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchParsingStatus, fetchRuntimeSettings, fetchSitesSettings, triggerScrapeNow, updateRuntimeSettings, updateSiteStatus, updateSitesBulkStatus } from "../api/client";
export function useSitesSettings() {
    return useQuery({
        queryKey: ["sites-settings"],
        queryFn: fetchSitesSettings,
    });
}
export function useRuntimeSettings() {
    return useQuery({
        queryKey: ["runtime-settings"],
        queryFn: fetchRuntimeSettings,
    });
}
export function useParsingStatus() {
    return useQuery({
        queryKey: ["parsing-status"],
        queryFn: fetchParsingStatus,
        refetchInterval: 30_000,
    });
}
export function useUpdateSiteStatus() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ siteId, isActive }) => updateSiteStatus(siteId, isActive),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["sites-settings"] });
            queryClient.invalidateQueries({ queryKey: ["overview"] });
            queryClient.invalidateQueries({ queryKey: ["price-changes"] });
            queryClient.invalidateQueries({ queryKey: ["best-deals"] });
        },
    });
}
export function useUpdateRuntimeSettings() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload) => updateRuntimeSettings(payload),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["runtime-settings"] });
            queryClient.invalidateQueries({ queryKey: ["parsing-status"] });
            queryClient.invalidateQueries({ queryKey: ["overview"] });
            queryClient.invalidateQueries({ queryKey: ["price-changes"] });
            queryClient.invalidateQueries({ queryKey: ["best-deals"] });
        },
    });
}
export function useUpdateSitesBulkStatus() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (items) => updateSitesBulkStatus(items),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["sites-settings"] });
            queryClient.invalidateQueries({ queryKey: ["parsing-status"] });
            queryClient.invalidateQueries({ queryKey: ["overview"] });
            queryClient.invalidateQueries({ queryKey: ["price-changes"] });
            queryClient.invalidateQueries({ queryKey: ["best-deals"] });
        },
    });
}
export function useTriggerScrapeNow() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: triggerScrapeNow,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["parsing-status"] });
            queryClient.invalidateQueries({ queryKey: ["overview"] });
            queryClient.invalidateQueries({ queryKey: ["price-changes"] });
            queryClient.invalidateQueries({ queryKey: ["best-deals"] });
        },
    });
}
