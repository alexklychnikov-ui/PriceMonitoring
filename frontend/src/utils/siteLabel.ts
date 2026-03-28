export function formatScraperLabel(siteName: string | null | undefined, siteId: number): string {
  if (!siteName) {
    return "—";
  }
  return `@${siteName}.py (${siteId})`;
}
