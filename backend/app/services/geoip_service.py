"""GeoIP + VPN/proxy lookup with graceful offline fallback.

Uses the free ip-api.com endpoint (no key). Private/loopback addresses and any
network failure fall back to a neutral default so the app never blocks on it.
The risk engine can also be handed a *simulated* context for live demos.
"""
from __future__ import annotations

import ipaddress
from dataclasses import asdict, dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("iaare.geoip")


@dataclass
class GeoInfo:
    ip: str
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_vpn: bool = False
    isp: Optional[str] = None
    source: str = "unknown"

    def as_dict(self) -> dict:
        return asdict(self)


def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_reserved
    except ValueError:
        return True


def lookup(ip: Optional[str]) -> GeoInfo:
    if not ip or _is_private(ip):
        # Local/dev address — return a neutral home location.
        return GeoInfo(ip=ip or "127.0.0.1", country="India", region="Delhi",
                       city="New Delhi", latitude=28.6139, longitude=77.2090,
                       is_vpn=False, isp="Local Network", source="local")

    if not settings.GEOIP_ENABLED:
        return GeoInfo(ip=ip, source="disabled")

    try:
        fields = "status,country,regionName,city,lat,lon,isp,proxy,hosting,query"
        resp = httpx.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": fields},
            timeout=4,
        )
        data = resp.json()
        if data.get("status") == "success":
            return GeoInfo(
                ip=data.get("query", ip),
                country=data.get("country"),
                region=data.get("regionName"),
                city=data.get("city"),
                latitude=data.get("lat"),
                longitude=data.get("lon"),
                is_vpn=bool(data.get("proxy") or data.get("hosting")),
                isp=data.get("isp"),
                source="ip-api",
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("GeoIP lookup failed for %s: %s", ip, exc)

    return GeoInfo(ip=ip, source="fallback")
