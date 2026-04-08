FROM jupyter/scipy-notebook:latest

# Install all GDAL-dependent packages together in one solve — mamba is much
# faster than conda for dependency resolution.
# rioxarray and geopandas share GDAL so batching avoids redundant re-solves.
RUN mamba install -c conda-forge --yes \
      "sqlite>=3.39" \
      gdal \
      rioxarray \
      geopandas \
    && mamba clean --all --yes

# Pure-Python packages install cleanly via pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
