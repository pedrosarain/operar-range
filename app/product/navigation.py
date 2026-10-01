from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(
    frozen=True,
)
class ProductRoute:
    slug: str
    label: str
    renderer: Callable[[], None]


PUBLIC_ROUTE_SLUGS = (
    "/dashboard",
    "/research",
    "/strategies",
    "/analytics",
    "/admin",
)


PUBLIC_ROUTE_LABELS = (
    "Dashboard",
    "Pesquisas",
    "Estratégias",
    "Analytics",
    "Administração",
)
