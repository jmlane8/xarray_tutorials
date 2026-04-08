# xarray_learn

A hands-on Jupyter notebook series for learning **xarray**, **Zarr**, **STAC**, **rioxarray**, and **GeoZarr** by building a real Sentinel-2 satellite data pipeline.

## What you'll build

A pipeline that queries public Sentinel-2 imagery over the Sacramento Valley, loads it lazily with Dask, computes NDVI, stores results in Zarr (locally and on S3), exports GeoTIFFs, and adds interactive ipywidgets controls — with each step explained from first principles.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- An AWS account with an S3 bucket and credentials at `~\.aws\credentials`

No local Python, conda, or GDAL installation needed — everything runs inside the container.

## Quickstart

**bash (Git Bash / WSL / Mac / Linux):**
```bash
git clone <this-repo>
cd xarray_learn

docker build -t xarray-learn .

docker run -p 8888:8888 \
  -v "$PWD":/home/jovyan/work \
  -v "$USERPROFILE/.aws":/home/jovyan/.aws:ro \
  xarray-learn
```

**cmd.exe:**
```bat
git clone <this-repo>
cd xarray_learn

docker build -t xarray-learn .

docker run -p 8888:8888 -v "%cd%":/home/jovyan/work -v "%USERPROFILE%\.aws":/home/jovyan/.aws:ro xarray-learn
```

Open the URL printed in the terminal (e.g. `http://127.0.0.1:8888/lab?token=...`) and navigate to `work/notebooks/`.

> **First build takes several minutes** — GDAL is installed via conda-forge.

## Notebooks

Run in order. Each notebook saves its output for the next one to read.

| # | Notebook | Teaches |
|---|----------|---------|
| 01 | `01_stac_query.ipynb` | STAC catalog → collection → item → asset |
| 02 | `02_xarray_load.ipynb` | Lazy loading, xarray dims/coords, Dask task graphs |
| 03 | `03_zarr_storage.ipynb` | Zarr chunks, `.zarray` metadata, local + S3 write |
| 04 | `04_ndvi_analysis.ipynb` | xarray arithmetic, `.where()`, dimension reduction |
| 05 | `05_widgets.ipynb` | ipywidgets observer pattern, band/date selector UI |
| 06 | `06_rioxarray.ipynb` | CRS, reprojection, polygon clip, COG export |
| 07 | `07_geozarr.ipynb` | GeoZarr conventions, `grid_mapping`, GDAL validation |

## S3 setup

The S3 cells in notebooks 03 and 07 are skipped unless you set your bucket name. Add this to the relevant cell before running:

```python
import os
os.environ["S3_BUCKET"] = "your-bucket-name"
```

Your credentials are picked up automatically from the mounted `~/.aws/credentials` file.

## Data

All data is downloaded at runtime from the [Element84 earth-search](https://earth-search.aws.element84.com/v1) public STAC catalog — no manual downloads required. Processed outputs are written to `data/` inside the project folder.

## Spec

See [SPEC.md](SPEC.md) for the full architecture, file structure, and per-notebook validation steps.
