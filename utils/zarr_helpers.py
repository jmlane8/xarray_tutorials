import xarray as xr
import numpy as np


def get_s3_store(bucket: str, path: str):
    """Return an s3fs.S3Map store for use with xarray.to_zarr() / open_zarr().

    Credentials are read from environment variables:
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION

    Args:
        bucket: S3 bucket name (no s3:// prefix)
        path:   key path inside the bucket e.g. "sentinel2.zarr"

    Returns:
        s3fs.S3Map object usable as a zarr store
    """
    import s3fs
    fs = s3fs.S3FileSystem()
    return s3fs.S3Map(f"s3://{bucket}/{path}", s3=fs)


def verify_roundtrip(original: xr.Dataset, loaded: xr.Dataset) -> None:
    """Assert that all variables in `loaded` match `original` for the first time slice.

    Raises AssertionError if any variable does not match within float tolerance.
    """
    for var in original.data_vars:
        orig_vals = original[var].isel(time=0).values
        load_vals = loaded[var].isel(time=0).compute().values
        assert np.allclose(orig_vals, load_vals, equal_nan=True), \
            f"Roundtrip mismatch in variable '{var}'"
    print("Roundtrip OK — all variables match.")
