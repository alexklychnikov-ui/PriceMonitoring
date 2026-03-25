export type Product = {
  id: number;
  site_id: number;
  name: string;
  brand?: string | null;
  model?: string | null;
  season?: string | null;
  tire_size?: string | null;
  radius?: string | null;
  current_price?: number | null;
  min_price?: number | null;
  max_price?: number | null;
  url: string;
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
