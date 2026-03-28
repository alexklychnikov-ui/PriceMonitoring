export type Product = {
  id: number;
  site_id: number;
  site_name?: string | null;
  name: string;
  brand?: string | null;
  model?: string | null;
  season?: string | null;
  spike?: boolean | null;
  tire_size?: string | null;
  radius?: string | null;
  current_price?: number | null;
  min_price?: number | null;
  max_price?: number | null;
  url: string;
  in_stock?: boolean | null;
  updated_at?: string | null;
};

export type Site = {
  id: number;
  name: string;
  base_url: string;
  catalog_url: string;
  is_active: boolean;
};

export type PriceHistory = {
  scraped_at: string;
  site_name: string;
  price: number;
  old_price?: number | null;
};

export type ParsingSettings = {
  winter: boolean;
  winter_studded: boolean;
  winter_non_studded: boolean;
  summer: boolean;
  parse_interval_hours: number;
};

export type AlertSettings = {
  enabled: boolean;
  min_change_pct: number;
  send_price_drop: boolean;
  send_price_rise: boolean;
};

export type RuntimeSettings = {
  parsing: ParsingSettings;
  alerts: AlertSettings;
};

export type ParsingStatus = {
  active_sites_count: number;
  interval_hours: number;
  last_started_at?: string | null;
  next_update_at?: string | null;
  running_sites: number;
};
