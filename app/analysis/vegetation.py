import ee

from app.models.analysis import (
    AnalysisResult,
    DataQuality,
    Methodology,
)

S2_DATASET = "COPERNICUS/S2_SR_HARMONIZED"


def mask_s2_clouds(image: ee.Image) -> ee.Image:
    """
    Mask clouds and cirrus from a Sentinel-2 SR image using QA60.

    QA60:
        Bit 10 -> clouds
        Bit 11 -> cirrus

    The Sentinel-2 SR Harmonized documentation provides this
    QA60 masking approach.
    """

    qa = image.select("QA60")

    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11

    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))

    # Sentinel-2 SR values are scaled by 10000.
    return image.updateMask(mask).divide(10000)


def add_ndvi(image: ee.Image) -> ee.Image:
    """
    Add an NDVI band to a Sentinel-2 image.

    NDVI = (NIR - RED) / (NIR + RED)

    Sentinel-2:
        B8 = NIR
        B4 = RED
    """

    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")

    return image.addBands(ndvi)


def build_ndvi_collection(
    aoi: ee.Geometry,
    start_date: str,
    end_date: str,
    max_cloud_percentage: float = 20.0,
) -> tuple[ee.ImageCollection, ee.Number]:
    """
    Build a cloud-masked Sentinel-2 NDVI collection.

    Returns:
        collection:
            Cloud-masked collection containing an NDVI band.

        source_image_count:
            Number of Sentinel-2 scenes before the
            scene-level cloud percentage filter.
    """

    source_collection = (
        ee.ImageCollection(S2_DATASET)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
    )

    source_image_count = source_collection.size()

    filtered_collection = (
        source_collection.filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                max_cloud_percentage,
            )
        )
        .map(mask_s2_clouds)
        .map(add_ndvi)
    )

    return filtered_collection, source_image_count


def calculate_valid_coverage(
    image: ee.Image,
    aoi: ee.Geometry,
    scale: int = 10,
) -> ee.Number:
    """
    Estimate the fraction of the AOI containing valid NDVI pixels.

    Returns:
        Value between 0 and 1.
    """

    valid_mask = image.select("NDVI").mask().rename("valid")

    coverage = valid_mask.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True,
    ).get("valid")

    return ee.Number(coverage)


def calculate_ndvi_statistics(
    ndvi_composite: ee.Image,
    aoi: ee.Geometry,
    scale: int = 10,
) -> ee.Dictionary:
    """
    Calculate regional NDVI statistics for the composite.
    """

    statistics = ndvi_composite.select("NDVI").reduceRegion(
        reducer=(
            ee.Reducer.mean()
            .combine(
                reducer2=ee.Reducer.min(),
                sharedInputs=True,
            )
            .combine(
                reducer2=ee.Reducer.max(),
                sharedInputs=True,
            )
            .combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True,
            )
        ),
        geometry=aoi,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True,
    )

    # Use ee.Algorithms.If to handle potentially missing keys
    def get_or_default(key):
        return ee.Algorithms.If(
            statistics.contains(key),
            statistics.getNumber(key),
            ee.Number(0.0)
        )

    return ee.Dictionary(
        {
            "mean": get_or_default("NDVI_mean"),
            "min": get_or_default("NDVI_min"),
            "max": get_or_default("NDVI_max"),
            "std_dev": get_or_default("NDVI_stdDev"),
        }
    )


def analyze_ndvi(
    aoi: ee.Geometry,
    start_date: str,
    end_date: str,
    max_cloud_percentage: float = 20.0,
    scale: int = 10,
) -> AnalysisResult:
    """
    Perform a basic regional NDVI analysis.

    Pipeline:

        Sentinel-2 SR Harmonized
            ↓
        AOI filtering
            ↓
        date filtering
            ↓
        scene cloud filtering
            ↓
        pixel cloud masking
            ↓
        NDVI calculation
            ↓
        median composite
            ↓
        regional statistics
            ↓
        structured AnalysisResult

    Args:
        aoi:
            Earth Engine geometry representing the AOI.

        start_date:
            Start date in YYYY-MM-DD format.

        end_date:
            End date in YYYY-MM-DD format.

        max_cloud_percentage:
            Maximum scene-level cloud percentage.

        scale:
            Analysis scale in meters.

    Returns:
        AnalysisResult containing NDVI statistics,
        data quality, methodology and limitations.
    """

    if not start_date:
        raise ValueError("start_date cannot be empty")

    if not end_date:
        raise ValueError("end_date cannot be empty")

    if scale <= 0:
        raise ValueError("scale must be greater than zero")

    if not 0 <= max_cloud_percentage <= 100:
        raise ValueError("max_cloud_percentage must be between 0 and 100")

    collection, source_image_count = build_ndvi_collection(
        aoi=aoi,
        start_date=start_date,
        end_date=end_date,
        max_cloud_percentage=max_cloud_percentage,
    )

    # Fetch counts early to avoid exception on empty collection
    counts = ee.Dictionary(
        {
            "source": source_image_count,
            "usable": collection.size(),
        }
    ).getInfo()

    if counts["usable"] == 0:
        raise ValueError(
            "No usable Sentinel-2 images were found "
            "for the supplied AOI and date range."
        )

    # Create one representative image for the period.
    ndvi_composite = collection.median()

    statistics_dict = calculate_ndvi_statistics(
        ndvi_composite=ndvi_composite,
        aoi=aoi,
        scale=scale,
    )

    valid_coverage_number = calculate_valid_coverage(
        image=ndvi_composite,
        aoi=aoi,
        scale=scale,
    )

    # Batch remaining Earth Engine API calls into a single request
    results = ee.Dictionary(
        {
            "statistics": statistics_dict,
            "valid_coverage": valid_coverage_number,
        }
    ).getInfo()

    limitations = [
        ("NDVI is a vegetation indicator and should not "
        "be interpreted as a direct measure of biomass."),
        "Cloud masking can leave areas with insufficient valid observations.",
        ("The median composite represents the selected "
        "time period rather than a single observation."),
        ("This PoC does not yet perform seasonal normalization "
        "or atmospheric-quality sensitivity analysis."),
    ]

    return AnalysisResult(
        analysis_type="ndvi_analysis",
        findings={
            "mean_ndvi": float(results["statistics"].get("mean", 0.0)),
            "minimum_ndvi": float(results["statistics"].get("min", 0.0)),
            "maximum_ndvi": float(results["statistics"].get("max", 0.0)),
            "ndvi_std_dev": float(results["statistics"].get("std_dev", 0.0)),
            "start_date": start_date,
            "end_date": end_date,
        },
        data_quality=DataQuality(
            source_image_count=int(counts["source"]),
            usable_image_count=int(counts["usable"]),
            valid_coverage=float(results["valid_coverage"])
            if results["valid_coverage"] is not None
            else 0.0,
        ),
        methodology=Methodology(
            dataset=S2_DATASET,
            resolution_m=scale,
            composite_method="median",
            cloud_masking=(
                "QA60 cloud and cirrus masking + scene CLOUDY_PIXEL_PERCENTAGE filter"
            ),
            index="NDVI = (B8 - B4) / (B8 + B4)",
        ),
        limitations=limitations,
        visualizations={},
    )
