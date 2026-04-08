# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repository sets up a Jupyter-based Docker environment for learning and experimenting with geospatial/scientific Python libraries:
- `xarray` — labeled N-dimensional arrays
- `zarr` — chunked, compressed array storage
- `pystac-client` / `planetary-computer` — STAC catalog access (e.g., Microsoft Planetary Computer)
- `rioxarray` — rasterio extension for xarray
- `odc-stac` — Open Data Cube STAC utilities
- `dask[complete]` — parallel/distributed computing
- `ipywidgets` — interactive Jupyter widgets

## Building and Running

```bash
# Build the image
docker build -t xarray-learn .

# Run (bash — Git Bash / WSL / Mac / Linux)
docker run -p 8888:8888 \
  -v "$PWD":/home/jovyan/work \
  -v "$USERPROFILE/.aws":/home/jovyan/.aws:ro \
  xarray-learn

# Run (cmd.exe)
# docker run -p 8888:8888 -v "%cd%":/home/jovyan/work -v "%USERPROFILE%\.aws":/home/jovyan/.aws:ro xarray-learn
```

# Project rules
- Use xarray + Zarr for all storage/analysis (chunked, dask-backed).
- Prefer pystac-client + odc-stac or rioxarray for STAC → Xarray.
- Always explain library concepts when making changes.
- Run notebook cells via jupyter nbconvert --execute or papermill after edits and fix failures.
- Verify Zarr roundtrips with xarray.open_zarr().
- Specification-driven: never code without referencing SPEC.md.

The base image comment references `jupyter/scipy-notebook` or similar — update the `FROM` line at the top of the Dockerfile to specify the actual base image before building.
