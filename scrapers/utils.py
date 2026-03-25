from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

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


def detect_season(name: str) -> str:
    value = name.lower()
    if any(token in value for token in ("winter", "зим", "шип", "ice")):
        return "winter"
    if any(token in value for token in ("summer", "лет", "sport")):
        return "summer"
    if any(token in value for token in ("allseason", "all season", "всесез")):
        return "allseason"
    return "unknown"


async def get_random_ua() -> str:
    return UserAgent().random


def split_brand_model(name: str) -> tuple[str, str]:
    tokens = name.strip().split()
    if not tokens:
        return "Unknown", "Unknown"
    if len(tokens) == 1:
        return tokens[0], "Unknown"
    return tokens[0], tokens[1]


def build_external_id(site_name: str, name: str, url: str) -> str:
    raw = f"{site_name}|{name}|{url}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
