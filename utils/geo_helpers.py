import xarray as xr
from pathlib import Path

# Default clip window: a 5 km × 5 km sub-region inside the Sacramento Valley AOI
# Units: metres in EPSG:32610 (UTM Zone 10N)
AOI_UTM = (620000, 4260000, 625000, 4265000)  # (minx, miny, maxx, maxy)


def clip_to_aoi(ds: xr.Dataset, bounds: tuple = AOI_UTM) -> xr.Dataset:
    """Clip an rioxarray-enabled Dataset to a bounding box in EPSG:32610.

    Args:
        ds:     Dataset with .rio accessor configured (spatial dims + CRS set)
        bounds: (minx, miny, maxx, maxy) in EPSG:32610 metres

    Returns:
        Clipped Dataset
    """
    from shapely.geometry import box
    geom = box(*bounds).__geo_interface__
    return ds.rio.clip([geom], crs="EPSG:32610")


def reproject_to_wgs84(ds: xr.Dataset) -> xr.Dataset:
    """Reproject a Dataset from its native CRS to EPSG:4326 (WGS84 geographic).

    Args:
        ds: Dataset with .rio accessor configured

    Returns:
        Reprojected Dataset in EPSG:4326
    """
    return ds.rio.reproject("EPSG:4326")


def write_cog(da: xr.DataArray, path: str) -> None:
    """Write a DataArray to a Cloud-Optimized GeoTIFF.

    Args:
        da:   2-D DataArray (single band, no time dimension)
        path: output file path e.g. "./data/ndvi.tif"
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    da.rio.to_raster(path, driver="COG")
    print(f"COG written → {path}")
