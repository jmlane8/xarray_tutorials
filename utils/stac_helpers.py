import pystac_client
from typing import List
import pystac

CATALOG_URL = "https://earth-search.aws.element84.com/v1"
DEFAULT_BBOX = [-121.5, 38.5, -121.0, 39.0]
DEFAULT_DATES = "2023-06-01/2023-08-31"


def search_sentinel2(
    bbox: List[float] = DEFAULT_BBOX,
    datetime: str = DEFAULT_DATES,
    max_cloud: int = 20,
    max_items: int = 10,
) -> List[pystac.Item]:
    """Search Element84 earth-search for Sentinel-2 L2A items.

    Args:
        bbox: [lon_min, lat_min, lon_max, lat_max] in WGS84
        datetime: ISO 8601 interval string e.g. "2023-06-01/2023-08-31"
        max_cloud: maximum cloud cover percentage (0-100)
        max_items: cap on results returned

    Returns:
        List of pystac.Item objects
    """
    catalog = pystac_client.Client.open(CATALOG_URL)
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=datetime,
        query={"eo:cloud_cover": {"lt": max_cloud}},
        max_items=max_items,
    )
    items = list(search.items())
    return items


def inspect_item(item: pystac.Item) -> None:
    """Pretty-print the key fields of a STAC Item."""
    print(f"ID:         {item.id}")
    print(f"Date:       {item.datetime}")
    print(f"Cloud cover:{item.properties.get('eo:cloud_cover')}%")
    print(f"BBox:       {item.bbox}")
    print(f"Assets:     {list(item.assets.keys())}")
    print(f"\nSample asset href (red band):")
    red = item.assets.get("red") or item.assets.get("B04")
    if red:
        print(f"  {red.href}")
