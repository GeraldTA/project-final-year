from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

# Band order required by BigEarthNet v2.0 S2 weights:
# B02,B03,B04,B05,B06,B07,B08,B8A,B11,B12


def make_scene(height: int, width: int, forest: bool) -> np.ndarray:
    blue = np.full((height, width), 0.12, np.float32)
    green = np.full((height, width), 0.14, np.float32)
    red = np.full((height, width), 0.10 if forest else 0.18, np.float32)
    b05 = np.full((height, width), 0.16, np.float32)
    b06 = np.full((height, width), 0.18, np.float32)
    b07 = np.full((height, width), 0.20, np.float32)
    nir = np.full((height, width), 0.55 if forest else 0.30, np.float32)
    b8a = np.full((height, width), 0.50 if forest else 0.28, np.float32)
    swir1 = np.full((height, width), 0.22 if forest else 0.30, np.float32)
    swir2 = np.full((height, width), 0.18 if forest else 0.28, np.float32)

    bands = np.stack([blue, green, red, b05, b06, b07, nir, b8a, swir1, swir2], axis=0)

    # Mimic Sentinel-2 scaling (reflectance*10000) with uint16 storage
    return (bands * 10000).astype(np.uint16)


def write_geotiff(path: Path, data: np.ndarray) -> None:
    height, width = data.shape[1], data.shape[2]

    # Arbitrary bbox in Zimbabwe-ish (WGS84)
    transform = from_origin(31.0, -17.0, 0.0001, 0.0001)
    crs = "EPSG:4326"

    path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=data.shape[0],
        dtype=data.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data)


def main() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    out_dir = backend_root / "data" / "raw"

    h, w = 256, 256
    before = make_scene(h, w, forest=True)
    after = make_scene(h, w, forest=False)

    before_path = out_dir / "sample_before_10band.tif"
    after_path = out_dir / "sample_after_10band.tif"

    write_geotiff(before_path, before)
    write_geotiff(after_path, after)

    print(f"Wrote {before_path}")
    print(f"Wrote {after_path}")


if __name__ == "__main__":
    main()
