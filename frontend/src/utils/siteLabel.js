export function formatScraperLabel(siteName, siteId) {
    if (!siteName) {
        return "—";
    }
    return `@${siteName}.py (${siteId})`;
}
