from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from fake_useragent import UserAgent


@dataclass
class TireSizeResult:
    tire_size: str
    radius: str
    width: int
    profile: int
    diameter: int


def parse_tire_size(name: str) -> TireSizeResult | None:
    m = re.search(r"(\d{3})/(\d{2,3})\s*(R)(\d{2})", name, re.IGNORECASE)
    if not m:
        return None
    width, profile, diameter = int(m.group(1)), int(m.group(2)), int(m.group(4))
    return TireSizeResult(
        tire_size=f"{width}/{profile}",
        radius=f"R{diameter}",
        width=width,
        profile=profile,
        diameter=diameter,
    )


def clean_price(raw: str) -> float | None:
    if not raw:
        return None
    normalized = raw.replace("\xa0", " ").replace("₽", "").replace("руб.", "").strip()
    normalized = re.sub(r"[^\d,.\s]", "", normalized)
    normalized = normalized.replace(" ", "")
    if not normalized:
        return None
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(",", "")
    elif "," in normalized:
        parts = normalized.split(",")
        if len(parts) == 2 and len(parts[1]) == 3:
            normalized = "".join(parts)
        else:
            normalized = normalized.replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def season_from_catalog_text(card_text: str | None) -> str | None:
    if not card_text or not card_text.strip():
        return None
    m = re.search(r"Сезон\s*:?\s*([а-яё]+)", card_text, flags=re.IGNORECASE)
    if not m:
        return None
    word = m.group(1).lower()
    if word.startswith("зим"):
        return "winter"
    if word.startswith("лет"):
        return "summer"
    if word.startswith("всесез"):
        return "allseason"
    return None


def detect_season(name: str, card_text: str | None = None) -> str:
    from_card = season_from_catalog_text(card_text)
    if from_card is not None:
        return from_card
    value = name.lower()
    if any(token in value for token in ("winter", "зим", "шип", "ice", "snow")):
        return "winter"
    if any(token in value for token in ("summer", "лет", "sport")):
        return "summer"
    if any(token in value for token in ("allseason", "all season", "всесез")):
        return "allseason"
    return "unknown"


async def get_random_ua() -> str:
    return UserAgent(os=["windows", "macos", "linux"]).random


def split_brand_model(name: str) -> tuple[str, str]:
    normalized = re.sub(r"\s+", " ", name).strip()
    if not normalized:
        return "Unknown", "Unknown"

    normalized = re.sub(r"^(легковая|грузовая)\s+шина\s+", "", normalized, flags=re.IGNORECASE)
    tokens = normalized.split()
    if not tokens:
        return "Unknown", "Unknown"

    service_tokens = {"шина", "автошина", "легковая", "грузовая"}
    idx = 0
    while idx < len(tokens) and tokens[idx].lower().strip(".,:;()[]") in service_tokens:
        idx += 1

    if idx >= len(tokens):
        return "Unknown", "Unknown"

    brand = tokens[idx]
    if brand.lower() == "н.камск" and idx + 1 < len(tokens):
        brand = tokens[idx + 1]
        idx += 1

    model_tokens = tokens[idx + 1 :]
    model = " ".join(model_tokens) if model_tokens else "Unknown"
    return brand, model


def canonicalize_url_for_id(url: str) -> str:
    p = urlparse((url or "").strip())
    path = p.path or "/"
    path = path.rstrip("/") or "/"
    netloc = (p.netloc or "").lower()
    scheme = (p.scheme or "https").lower()
    return urlunparse((scheme, netloc, path, "", "", ""))


def build_external_id(site_name: str, name: str, url: str) -> str:
    norm_name = " ".join((name or "").split())
    raw = f"{site_name}|{norm_name}|{canonicalize_url_for_id(url)}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
