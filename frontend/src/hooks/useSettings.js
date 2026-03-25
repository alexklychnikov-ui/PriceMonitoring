import { useQuery } from "@tanstack/react-query";
import { fetchSitesSettings } from "../api/client";
export function useSitesSettings() {
    return useQuery({
        queryKey: ["sites-settings"],
        queryFn: fetchSitesSettings,
    });
}
