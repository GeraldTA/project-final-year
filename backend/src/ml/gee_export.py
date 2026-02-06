"""GEE export helpers for ML inference.

Provides a small, dependency-light path to download a multi-band GeoTIFF
directly from Google Earth Engine using ee.Image.getDownloadURL.

We intentionally keep Earth Engine imports lazy to avoid import-time failures
in environments where EE isn't configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


S2_10BAND_GEE_BANDS: Tuple[str, ...] = (
    "B2",   # Blue 10m
    "B3",   # Green 10m
    "B4",   # Red 10m
    "B5",   # Red Edge 20m
    "B6",   # Red Edge 20m
    "B7",   # Red Edge 20m
    "B8",   # NIR 10m
    "B8A",  # Narrow NIR 20m
    "B11",  # SWIR 20m
    "B12",  # SWIR 20m
)


@dataclass(frozen=True)
class Bounds:
    west: float
    south: float
    east: float
    north: float

    @staticmethod
    def from_any(payload: Dict[str, Any]) -> "Bounds":
        """Accept multiple common bounds formats."""
        if {"west", "south", "east", "north"}.issubset(payload.keys()):
            return Bounds(
                west=float(payload["west"]),
                south=float(payload["south"]),
                east=float(payload["east"]),
                north=float(payload["north"]),
            )

        # Frontend monitoring format
        if {"min_lng", "min_lat", "max_lng", "max_lat"}.issubset(payload.keys()):
            return Bounds(
                west=float(payload["min_lng"]),
                south=float(payload["min_lat"]),
                east=float(payload["max_lng"]),
                north=float(payload["max_lat"]),
            )

        raise ValueError("Bounds must include either west/south/east/north or min_lat/min_lng/max_lat/max_lng")


def _initialize_ee(project_id: Optional[str] = None) -> None:
    """Initialize Earth Engine if not already initialized."""
    import os

    import ee  # type: ignore

    try:
        # If ee is already initialized, this is a no-op.
        ee.data.getInfo("")
        return
    except Exception:
        pass

    if project_id is None:
        project_id = os.environ.get("GEE_PROJECT_ID")

    if project_id is None:
        project_file = Path(__file__).resolve().parents[2] / "gee_project_id.txt"
        if project_file.exists():
            project_id = project_file.read_text(encoding="utf-8").strip() or None

    try:
        if project_id:
            ee.Initialize(project=project_id)
        else:
            ee.Initialize()
    except Exception as e:
        raise RuntimeError(
            "Google Earth Engine is not authenticated/initialized. "
            "Run `earthengine authenticate` (or set service account creds) and try again. "
            f"Original error: {e}"
        )


def _cache_key(
    *,
    bounds: Bounds,
    start_date: str,
    end_date: str,
    max_cloud_cover: float,
    scale: int,
) -> str:
    raw = f"{bounds.west},{bounds.south},{bounds.east},{bounds.north}|{start_date}|{end_date}|{max_cloud_cover}|{scale}|{'-'.join(S2_10BAND_GEE_BANDS)}"
    return sha1(raw.encode("utf-8")).hexdigest()[:16]


def export_s2_10band_geotiff(
    *,
    bounds: Bounds,
    start_date: str,
    end_date: str,
    output_dir: Path,
    max_cloud_cover: float = 30.0,
    scale: int = 10,
    dimensions: Optional[int] = 512,
    force: bool = False,
) -> Dict[str, Any]:
    """Export a 10-band Sentinel-2 SR composite to a local multi-band GeoTIFF.

    Returns a dict with `path` plus metadata about the composite.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(
        bounds=bounds,
        start_date=start_date,
        end_date=end_date,
        max_cloud_cover=max_cloud_cover,
        scale=scale,
    )

    tif_path = output_dir / f"s2_10band_{key}.tif"
    meta_path = output_dir / f"s2_10band_{key}.json"

    if tif_path.exists() and not force:
        return {
            "path": str(tif_path),
            "cached": True,
            "start_date": start_date,
            "end_date": end_date,
            "bounds": bounds.__dict__,
            "bands": list(S2_10BAND_GEE_BANDS),
            "scale": scale,
            "dimensions": dimensions,
            "max_cloud_cover": max_cloud_cover,
            "metadata_path": str(meta_path) if meta_path.exists() else None,
        }

    _initialize_ee()

    import ee  # type: ignore
    import requests
    import shutil
    import tempfile
    import zipfile

    roi = ee.Geometry.Rectangle([bounds.west, bounds.south, bounds.east, bounds.north])

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", float(max_cloud_cover)))
    )

    try:
        size = int(collection.size().getInfo())
    except Exception as e:
        raise RuntimeError(f"Failed querying Earth Engine collection: {e}")

    if size == 0:
        raise ValueError(
            f"No Sentinel-2 images found in date range {start_date} to {end_date} "
            f"with cloud cover < {max_cloud_cover}%. "
            f"Try: (1) expanding the date range, (2) increasing max_cloud_cover, or "
            f"(3) choosing a different time period with more satellite coverage."
        )

    # Use median composite for stability.
    composite = collection.median().clip(roi).select(list(S2_10BAND_GEE_BANDS))

    params: Dict[str, Any] = {
        "region": roi,
        "filePerBand": False,
        "format": "GEO_TIFF",
    }

    # Earth Engine does NOT allow (scale AND dimensions) simultaneously.
    # For ML inference we prefer dimensions to keep downloads small.
    if dimensions is not None:
        params["dimensions"] = int(dimensions)
    else:
        params["scale"] = int(scale)

    try:
        url = composite.getDownloadURL(params)
    except Exception as e:
        raise RuntimeError(f"Failed to create download URL from Earth Engine: {e}")

    with tempfile.TemporaryDirectory(prefix="gee_s2_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        download_path = tmpdir_path / "download.bin"

        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(download_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        magic = download_path.read_bytes()[:4]

        # ZIP: PK\x03\x04
        if magic.startswith(b"PK"):
            with zipfile.ZipFile(download_path, "r") as z:
                z.extractall(tmpdir_path)

            tifs = list(tmpdir_path.rglob("*.tif")) + list(tmpdir_path.rglob("*.tiff"))
            if not tifs:
                raise RuntimeError("Earth Engine download ZIP did not contain a GeoTIFF")

            # Choose the largest tif (usually the full multi-band composite).
            chosen = max(tifs, key=lambda p: p.stat().st_size)
            shutil.copyfile(chosen, tif_path)

        # GeoTIFF (little-endian II*\x00 or big-endian MM\x00*)
        elif magic in (b"II*\x00", b"MM\x00*"):
            shutil.copyfile(download_path, tif_path)

        else:
            raise RuntimeError("Unexpected download format from Earth Engine (not ZIP or GeoTIFF)")

    metadata = {
        "cached": False,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "start_date": start_date,
        "end_date": end_date,
        "bounds": bounds.__dict__,
        "bands": list(S2_10BAND_GEE_BANDS),
        "scale": scale,
        "dimensions": dimensions,
        "max_cloud_cover": max_cloud_cover,
        "collection_size": size,
        "source": "GEE COPERNICUS/S2_SR_HARMONIZED median composite",
    }
    try:
        meta_path.write_text(__import__("json").dumps(metadata, indent=2), encoding="utf-8")
    except Exception:
        pass

    return {"path": str(tif_path), "cached": False, **metadata, "metadata_path": str(meta_path)}
