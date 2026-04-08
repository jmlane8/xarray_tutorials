# SPEC.md — Sentinel-2 STAC → Xarray → Zarr → rioxarray → GeoZarr Learning Project

## Goal

Build a multi-notebook Jupyter environment that teaches xarray, Zarr, STAC, rioxarray, and GeoZarr from first principles by constructing a real geospatial analysis pipeline. The learner has intermediate Python experience (numpy/pandas) but is new to these libraries. The outcome is deep conceptual understanding of each tool, not just a working script.

---

## Area of Interest

| Parameter | Value |
|-----------|-------|
| **Location** | Sacramento Valley, California (agricultural, strong NDVI signal) |
| **Bounding box** | `[-121.5, 38.5, -121.0, 39.0]` (lon_min, lat_min, lon_max, lat_max) |
| **Date range** | `2023-06-01` to `2023-08-31` (low cloud cover, active growing season) |
| **Max cloud cover** | 20% |
| **Target scenes** | 2–3 scenes (one per month) |
| **Bands** | B02 (Blue), B03 (Green), B04 (Red), B08 (NIR) |
| **Collection** | `sentinel-2-l2a` |
| **CRS** | EPSG:32610 (UTM Zone 10N — native for this region) |

---

## Architecture

```
STAC Catalog (Element84/AWS)
        │
        │  pystac-client  (search by bbox + date + cloud cover)
        ▼
   STAC Items (metadata + COG asset URLs)
        │
        │  odc-stac  (lazy load → xarray.Dataset, CRS-aligned)
        ▼
  xarray.Dataset  (dims: time × band × y × x, dask-backed, EPSG:32610)
        │
        │  ufunc / vectorize  (NDVI = (NIR - Red) / (NIR + Red))
        ▼
  Processed Dataset  (original bands + ndvi variable)
        │
        ├──────────────────────────────────────────┐
        │  zarr + s3fs                              │  zarr + local filesystem
        ▼                                           ▼
  s3://bucket/sentinel2.zarr              ./data/sentinel2_local.zarr
        │
        │  xarray.open_zarr()  (verify roundtrip)
        ▼
  ipywidgets  (band/date selectors → matplotlib replot)
        │
        ▼
  rioxarray  (rio accessor: set_spatial_dims, write_crs,
              reproject → EPSG:4326, clip to polygon, to_raster COG)
        │
        ▼
  GeoZarr  (write Zarr with CF + GeoZarr spatial metadata conventions,
             validate with GDAL/rioxarray as external reader)
```

### Key design decisions

- **Lazy loading everywhere**: xarray holds Dask arrays until `.compute()` is explicitly called. This is the core mental model to build.
- **odc-stac as the STAC→xarray bridge**: `odc.stac.load()` handles CRS alignment, reprojection, and band stacking in one call, avoiding manual COG wrangling.
- **Zarr chunking strategy**: chunk along `(time=1, y=256, x=256)` — one scene per time chunk, spatial chunks sized for typical analysis windows. Chunking decisions will be examined explicitly.
- **S3 writes via s3fs**: Zarr's `FSStore` wraps s3fs transparently. Credentials injected via environment variables, never hardcoded.
- **No cloud credentials in notebooks**: All S3 config loaded from `os.environ` or `~/.aws/credentials`.
- **rioxarray as the spatial accessor layer**: rioxarray extends xarray with a `.rio` accessor that exposes CRS management, reprojection, clipping, and GeoTIFF export without replacing xarray's data model.
- **GeoZarr as the interoperability standard**: GeoZarr is a set of conventions (built on CF and Zarr) for encoding CRS and spatial metadata so that non-xarray tools (GDAL, QGIS) can read Zarr stores correctly. It is not a separate library — it is metadata written into `.zattrs`.

---

## File Structure

```
xarray_learn/
├── Dockerfile                   # Jupyter base image + all deps
├── requirements.txt             # Pinned dependencies (see below)
├── CLAUDE.md
├── SPEC.md                      # This file
├── data/
│   └── .gitkeep                 # Local zarr stores written here (git-ignored)
├── notebooks/
│   ├── 01_stac_query.ipynb      # STAC search, item inspection, asset URLs
│   ├── 02_xarray_load.ipynb     # COG → xarray.Dataset via odc-stac, Dask intro
│   ├── 03_zarr_storage.ipynb    # Write/read zarr locally, then to S3
│   ├── 04_ndvi_analysis.ipynb   # xarray computation, time series, masking
│   ├── 05_widgets.ipynb         # ipywidgets band/date selector + matplotlib
│   ├── 06_rioxarray.ipynb       # spatial dims, CRS, reproject, clip, COG export
│   └── 07_geozarr.ipynb         # GeoZarr conventions, spatial metadata, GDAL validation
└── utils/
    ├── __init__.py
    ├── stac_helpers.py          # search_sentinel2(), inspect_item()
    ├── zarr_helpers.py          # get_s3_store(), verify_roundtrip()
    └── geo_helpers.py           # clip_to_aoi(), reproject_to_wgs84(), write_cog()
```

---

## Dependencies (`requirements.txt`)

```
xarray>=2024.1
zarr>=2.17
pystac-client>=0.7
odc-stac>=0.3.9
rioxarray>=0.15
dask[complete]>=2024.1
s3fs>=2024.1
ipywidgets>=8.1
matplotlib>=3.8
numpy>=1.26
shapely>=2.0
geopandas>=0.14
gdal>=3.8          # for GeoZarr validation via gdalinfo
```

Update the `Dockerfile` `FROM` line to `FROM jupyter/scipy-notebook:latest` and add `COPY requirements.txt .` then `RUN pip install -r requirements.txt`.

---

## Notebook Specifications

### `01_stac_query.ipynb` — STAC Query

**Purpose**: Understand what STAC is, how to search a catalog, and what a STAC Item contains.

**Cells (in order)**:
1. Import `pystac_client`. Connect to `https://earth-search.aws.element84.com/v1`.
2. Search `sentinel-2-l2a` with bbox, date range, `eo:cloud_cover < 20`. Print item count.
3. Inspect one item: print `.id`, `.datetime`, `.properties`, `.assets.keys()`.
4. Extract the B04 asset href (a COG URL). Print it and explain its structure.
5. Call `utils.stac_helpers.search_sentinel2()` to confirm the helper works.

**Validation**:
```python
assert len(items) >= 2, "Expected at least 2 scenes in date range"
assert "red" in items[0].assets or "B04" in items[0].assets, "Missing red band asset"
assert items[0].bbox is not None, "Item should have a bounding box"
```

**Learning checkpoint — Q&A**:
> Q1: What is a STAC Item, and how does it differ from the actual raster data?
> Q2: What does the `eo:cloud_cover` property represent, and where does it live in the STAC data model?
> Q3: Why is the asset href a URL pointing to a COG rather than raw data?

---

### `02_xarray_load.ipynb` — Xarray + Dask Loading

**Purpose**: Load STAC items into a lazy xarray.Dataset and understand Dask-backed arrays.

**Cells (in order)**:
1. Import `odc.stac`, `xarray`, `dask`. Start a local Dask client. Print dashboard URL.
2. Call `odc.stac.load(items, bands=["B02","B03","B04","B08"], crs="EPSG:32610", resolution=20)`.
3. Print `ds` — examine `.dims`, `.coords`, `.data_vars`, `.chunks`.
4. Print `ds["B04"].data` — show it is a Dask array (not yet computed).
5. Select one time slice: `ds.isel(time=0)`. Plot B04 with `matplotlib.imshow`.
6. Call `.compute()` on the time slice. Observe memory usage change.
7. Examine the task graph: `ds["B04"].data.visualize()` (save to `data/task_graph.png`).

**Validation**:
```python
import dask.array as da
assert isinstance(ds["B04"].data, da.Array), "Should be Dask-backed"
assert set(ds.data_vars) == {"B02","B03","B04","B08"}, "Missing bands"
assert "time" in ds.dims and "y" in ds.dims and "x" in ds.dims
assert ds.rio.crs.to_epsg() == 32610, "Wrong CRS"
```

**Learning checkpoint — Q&A**:
> Q1: What does "lazy loading" mean? At what point does data actually transfer from the COG URL to memory?
> Q2: What do `.dims`, `.coords`, and `.data_vars` each represent in an xarray Dataset?
> Q3: What is a Dask task graph and why is it useful to inspect one?
> Q4: What happens to memory when you call `.compute()`? What's the tradeoff?

---

### `03_zarr_storage.ipynb` — Zarr Read/Write

**Purpose**: Understand Zarr's storage model (chunks, compressors, stores) and do a full local + S3 roundtrip.

**Cells (in order)**:
1. **Local write**: `ds.to_zarr("./data/sentinel2_local.zarr", mode="w")`. Inspect the directory structure with `os.walk`.
2. Examine `.zmetadata`, `.zarray` files manually — explain what they encode.
3. **Local read**: `ds2 = xr.open_zarr("./data/sentinel2_local.zarr")`. Assert shapes and values match.
4. **Chunking experiment**: Re-save with different chunk sizes `(time=1, y=512, x=512)`. Compare directory sizes.
5. **S3 write**:
   ```python
   import s3fs, zarr
   # Credentials from environment: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
   fs = s3fs.S3FileSystem()
   store = zarr.storage.FSStore("s3://YOUR_BUCKET/sentinel2.zarr", fs=fs)
   ds.to_zarr(store, mode="w")
   ```
6. **S3 read**: `ds3 = xr.open_zarr(store)`. Call `utils.zarr_helpers.verify_roundtrip(ds, ds3)`.

**`utils/zarr_helpers.py`**:
```python
import xarray as xr
import numpy as np

def get_s3_store(bucket: str, path: str):
    import s3fs, zarr
    fs = s3fs.S3FileSystem()
    return zarr.storage.FSStore(f"s3://{bucket}/{path}", fs=fs)

def verify_roundtrip(original: xr.Dataset, loaded: xr.Dataset) -> None:
    for var in original.data_vars:
        orig_vals = original[var].isel(time=0).values
        load_vals = loaded[var].isel(time=0).compute().values
        assert np.allclose(orig_vals, load_vals, equal_nan=True), f"Mismatch in {var}"
    print("Roundtrip OK: all variables match.")
```

**Validation**:
```python
import os
assert os.path.isdir("./data/sentinel2_local.zarr"), "Zarr store not created"
assert os.path.isfile("./data/sentinel2_local.zarr/.zmetadata"), "Missing metadata"
verify_roundtrip(ds, ds2)
```

**Learning checkpoint — Q&A**:
> Q1: How does Zarr store a dataset — what is physically written to disk or S3?
> Q2: What is a "chunk" in Zarr and why does chunk size matter for read performance?
> Q3: What does `.zarray` contain and why does xarray need it to open a Zarr store?
> Q4: What is the role of `s3fs` — is it a Zarr concept or a filesystem abstraction?

---

### `04_ndvi_analysis.ipynb` — Xarray Analysis

**Purpose**: Use xarray's computation model to derive NDVI, mask clouds, and produce a time-series plot.

**Cells (in order)**:
1. Open from local zarr: `ds = xr.open_zarr("./data/sentinel2_local.zarr")`.
2. Compute NDVI: `ndvi = (ds["B08"] - ds["B04"]) / (ds["B08"] + ds["B04"])`. Assign as new variable.
3. Mask invalid pixels: `ndvi = ndvi.where(ndvi >= -1).where(ndvi <= 1)`.
4. Spatial mean per time step: `ndvi.mean(dim=["x","y"]).compute()`. Plot time series.
5. Find date of maximum NDVI: `ndvi.mean(dim=["x","y"]).idxmax(dim="time")`.
6. Plot the NDVI map for that date using `matplotlib.imshow` with a `RdYlGn` colormap.
7. Save the enriched dataset (original bands + ndvi) back to zarr.

**Validation**:
```python
assert "ndvi" in ds_enriched.data_vars
ndvi_vals = ds_enriched["ndvi"].isel(time=0).values
assert ndvi_vals.min() >= -1.0 - 1e-6
assert ndvi_vals.max() <= 1.0 + 1e-6
```

**Learning checkpoint — Q&A**:
> Q1: When you write `(ds["B08"] - ds["B04"])`, does xarray compute anything immediately? Why not?
> Q2: What does `.where()` do in xarray — how is it different from boolean indexing in numpy?
> Q3: What does `mean(dim=["x","y"])` return — what are its remaining dimensions?
> Q4: What is the difference between `isel()` and `sel()`?

---

### `05_widgets.ipynb` — ipywidgets

**Purpose**: Add basic interactivity — a band dropdown and date slider that replot a map on change.

**Cells (in order)**:
1. Open zarr store. Confirm available bands and time coordinates.
2. Create a band `Dropdown` with options `["B02","B03","B04","B08","ndvi"]`.
3. Create a date `SelectionSlider` over `ds.time.values`.
4. Write an `update_plot(band, date)` function that selects the slice and calls `ax.imshow(...)`.
5. Wire widgets with `ipywidgets.interactive(update_plot, band=band_widget, date=date_widget)`.
6. Display with `ipywidgets.VBox([band_widget, date_widget, out])`.

**Validation**:
```python
import ipywidgets as w
assert isinstance(band_widget, w.Dropdown)
assert isinstance(date_widget, w.SelectionSlider)
# Manually trigger: update_plot("ndvi", ds.time.values[0]) — should not raise
```

**Learning checkpoint — Q&A**:
> Q1: What is the observer pattern and how does `ipywidgets.interactive()` implement it?
> Q2: Why must the plot update function call `plt.clf()` or clear the axes before redrawing?
> Q3: What is the difference between `interact()` and `interactive()` in ipywidgets?

---

### `06_rioxarray.ipynb` — rioxarray Spatial Operations

**Purpose**: Learn rioxarray's `.rio` accessor to manage CRS, reproject, clip to a polygon, and export a GeoTIFF/COG.

**Cells (in order)**:
1. Open zarr: `ds = xr.open_zarr("./data/sentinel2_local.zarr")`. Show that `ds.rio.crs` is `None` initially (CRS not yet attached).
2. **Set spatial dims and CRS**:
   ```python
   ds = ds.rio.set_spatial_dims(x_dim="x", y_dim="y")
   ds = ds.rio.write_crs("EPSG:32610")
   print(ds.rio.crs)          # Should print EPSG:32610
   print(ds.rio.transform())  # Affine transform
   print(ds.rio.bounds())     # (left, bottom, right, top) in UTM metres
   ```
3. **Reproject to WGS84**:
   ```python
   ds_wgs84 = ds.rio.reproject("EPSG:4326")
   print(ds_wgs84.rio.crs)    # EPSG:4326
   print(ds_wgs84.rio.bounds()) # Now in degrees
   ```
4. **Clip to a polygon** (a small farm field inside the AOI):
   ```python
   from shapely.geometry import box
   # A 5km × 5km sub-window in UTM
   clip_geom = box(620000, 4260000, 625000, 4265000)
   ds_clipped = ds.rio.clip([clip_geom.__geo_interface__], crs="EPSG:32610")
   print(ds_clipped.rio.bounds())
   ```
5. **Export single-band GeoTIFF**:
   ```python
   ndvi_scene = ds_clipped["ndvi"].isel(time=0)
   ndvi_scene.rio.to_raster("./data/ndvi_scene0.tif")
   ```
6. **Export Cloud-Optimized GeoTIFF**:
   ```python
   ndvi_scene.rio.to_raster("./data/ndvi_scene0_cog.tif", driver="COG")
   ```
7. Call `utils.geo_helpers.write_cog()` and verify output with `gdalinfo ./data/ndvi_scene0_cog.tif`.

**`utils/geo_helpers.py`**:
```python
import xarray as xr
from pathlib import Path

AOI_UTM = (620000, 4260000, 625000, 4265000)  # (minx, miny, maxx, maxy) EPSG:32610

def clip_to_aoi(ds: xr.Dataset, bounds: tuple = AOI_UTM) -> xr.Dataset:
    from shapely.geometry import box
    geom = box(*bounds).__geo_interface__
    return ds.rio.clip([geom], crs="EPSG:32610")

def reproject_to_wgs84(ds: xr.Dataset) -> xr.Dataset:
    return ds.rio.reproject("EPSG:4326")

def write_cog(da: xr.DataArray, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    da.rio.to_raster(path, driver="COG")
    print(f"COG written to {path}")
```

**Validation**:
```python
import rioxarray  # noqa — registers .rio accessor
assert ds.rio.crs.to_epsg() == 32610
assert ds_wgs84.rio.crs.to_epsg() == 4326
assert ds_clipped.rio.width < ds.rio.width, "Clip should reduce spatial extent"
import os
assert os.path.isfile("./data/ndvi_scene0_cog.tif"), "COG not written"
```

**Learning checkpoint — Q&A**:
> Q1: What does `rio.write_crs()` actually do — where is the CRS stored in the xarray object?
> Q2: What is an Affine transform and what does it encode about a raster?
> Q3: When you reproject from EPSG:32610 to EPSG:4326, what happens to pixel values and resolution?
> Q4: What makes a GeoTIFF "Cloud-Optimized" — how does its internal structure differ from a regular GeoTIFF?

---

### `07_geozarr.ipynb` — GeoZarr Conventions

**Purpose**: Understand the GeoZarr specification — how CRS and spatial metadata are encoded in Zarr `.zattrs` so that GDAL and other tools can read the store without xarray.

**Background (markdown cell)**:
> GeoZarr is not a library — it is a set of conventions that specify how to embed spatial metadata (CRS, grid mapping, coordinates) inside a Zarr store's `.zattrs` JSON files, following CF (Climate and Forecast) conventions. A correctly written GeoZarr store can be opened by GDAL ≥ 3.8, QGIS, and other tools that don't know about xarray.

**Cells (in order)**:
1. Open the enriched zarr from notebook 04: `ds = xr.open_zarr("./data/sentinel2_local.zarr")`.
2. Attach CRS with rioxarray: `ds = ds.rio.set_spatial_dims(x_dim="x", y_dim="y").rio.write_crs("EPSG:32610")`.
3. **Inspect what rioxarray writes to `.zattrs`**:
   ```python
   import zarr, json
   z = zarr.open("./data/sentinel2_local.zarr")
   print(json.dumps(dict(z["B04"].attrs), indent=2))
   # Look for "grid_mapping", "crs_wkt", "_CRS" keys
   ```
4. **Write a GeoZarr-compliant store** — add the required CF attributes manually and via `write_crs`:
   ```python
   ds_geo = ds.rio.write_crs("EPSG:32610", grid_mapping_name="spatial_ref")
   ds_geo.to_zarr("./data/sentinel2_geozarr.zarr", mode="w")
   ```
5. **Validate with GDAL** (run shell from notebook):
   ```python
   import subprocess
   result = subprocess.run(
       ["gdalinfo", "./data/sentinel2_geozarr.zarr/B04"],
       capture_output=True, text=True
   )
   print(result.stdout)
   # Look for: "Coordinate System is: PROJCRS["WGS 84 / UTM zone 10N"..."
   ```
6. **Validate with rioxarray as a fresh reader** — open without any prior xarray context:
   ```python
   import rioxarray
   da = rioxarray.open_rasterio("./data/sentinel2_geozarr.zarr/B04")
   print(da.rio.crs)   # Should resolve to EPSG:32610 from metadata alone
   ```
7. **Write to S3 with GeoZarr metadata**:
   ```python
   store = utils.zarr_helpers.get_s3_store("YOUR_BUCKET", "sentinel2_geozarr.zarr")
   ds_geo.to_zarr(store, mode="w")
   ```
8. Examine the `.zattrs` JSON of the S3 store and compare to the local one.

**Validation**:
```python
import zarr, json
z = zarr.open("./data/sentinel2_geozarr.zarr")
b04_attrs = dict(z["B04"].attrs)
assert "grid_mapping" in b04_attrs, "Missing grid_mapping attribute — not GeoZarr compliant"

result = subprocess.run(
    ["gdalinfo", "./data/sentinel2_geozarr.zarr/B04"],
    capture_output=True, text=True
)
assert "UTM zone 10N" in result.stdout or "32610" in result.stdout, "GDAL cannot read CRS"

import rioxarray
da = rioxarray.open_rasterio("./data/sentinel2_geozarr.zarr/B04")
assert da.rio.crs is not None, "rioxarray cannot resolve CRS from metadata"
assert da.rio.crs.to_epsg() == 32610
```

**Learning checkpoint — Q&A**:
> Q1: What is the difference between the CRS being stored in xarray's in-memory attributes vs. in Zarr's `.zattrs` on disk?
> Q2: What is a `grid_mapping` variable in CF conventions and why does GDAL require it?
> Q3: If you open a GeoZarr store in QGIS without any Python, how does QGIS know where the data is located on Earth?
> Q4: What would break if you saved a Zarr store with `ds.to_zarr()` but skipped `rio.write_crs()` before saving?

---

## `utils/stac_helpers.py`

```python
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
    print(f"ID:       {item.id}")
    print(f"Date:     {item.datetime}")
    print(f"Cloud:    {item.properties.get('eo:cloud_cover')}%")
    print(f"Assets:   {list(item.assets.keys())}")
```

---

## Validation Summary

Each notebook must pass its inline assertions before moving to the next. Run all notebooks in order to validate the full pipeline:

```bash
jupyter nbconvert --to notebook --execute notebooks/01_stac_query.ipynb   --output notebooks/01_stac_query_out.ipynb
jupyter nbconvert --to notebook --execute notebooks/02_xarray_load.ipynb  --output notebooks/02_xarray_load_out.ipynb
jupyter nbconvert --to notebook --execute notebooks/03_zarr_storage.ipynb --output notebooks/03_zarr_storage_out.ipynb
jupyter nbconvert --to notebook --execute notebooks/04_ndvi_analysis.ipynb --output notebooks/04_ndvi_analysis_out.ipynb
jupyter nbconvert --to notebook --execute notebooks/05_widgets.ipynb       --output notebooks/05_widgets_out.ipynb
jupyter nbconvert --to notebook --execute notebooks/06_rioxarray.ipynb    --output notebooks/06_rioxarray_out.ipynb
jupyter nbconvert --to notebook --execute notebooks/07_geozarr.ipynb      --output notebooks/07_geozarr_out.ipynb
```

Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, and `S3_BUCKET` as environment variables before executing notebooks 03 and 07.

---

## Build Sequence

1. Build (conda GDAL install takes a few minutes on first build):
   ```
   docker build -t xarray-learn .
   ```
2. Run — mounts your project files and AWS credentials (Windows):
   ```
   docker run -p 8888:8888 -v "%cd%":/home/jovyan/work -v "%USERPROFILE%\.aws":/home/jovyan/.aws:ro xarray-learn
   ```
3. Open Jupyter at `localhost:8888` and navigate to `work/notebooks/`.
4. Set `S3_BUCKET` in a notebook cell (`os.environ["S3_BUCKET"] = "your-bucket-name"`) before running the S3 cells in notebooks 03 and 07.
5. Execute notebooks 01–07 in order.

---

## Learning Progression

| Notebook | Core concept unlocked |
|----------|-----------------------|
| 01 | STAC data model: catalog → collection → item → asset |
| 02 | Lazy vs eager evaluation; xarray's labeled dimensions; Dask task graphs |
| 03 | Zarr's chunk/metadata storage model; S3 as a filesystem abstraction |
| 04 | xarray computation model; broadcasting; `where` masking; dimension reduction |
| 05 | Reactive UI with ipywidgets; observer pattern; connecting widgets to xarray slices |
| 06 | rioxarray `.rio` accessor; CRS attachment; reprojection; polygon clipping; COG export |
| 07 | GeoZarr conventions; CF grid_mapping; spatial metadata in `.zattrs`; GDAL interop |
