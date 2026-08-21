import ee

from app.models.analysis import (
    AnalysisResult,
    DataQuality,
    Methodology,
)

DW_DATASET = "GOOGLE/DYNAMICWORLD/V1"
LAND_COVER_CLASSES = {
    0: "water",
    1: "trees",
    2: "grass",
    3: "flooded_vegetation",
    4: "crops",
    5: "shrub_and_scrub",
    6: "built",
    7: "bare",
    8: "snow_and_ice",
}


def build_landcover_collection(
    aoi: ee.Geometry,
    start_date: str,
    end_date: str,
) -> tuple[ee.ImageCollection, ee.Number]:
    """
    Build a Dynamic World collection filtered
    by AOI and date.

    Returns:
        collection:
            Dynamic World images for the AOI and period.

        source_image_count:
            Number of source images found (as an EE Number).
    """

    collection = (
        ee.ImageCollection(DW_DATASET)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
    )

    source_image_count = collection.size()

    return collection, source_image_count


def build_landcover_histogram(
    composite: ee.Image,
    aoi: ee.Geometry,
    scale: int = 10,
) -> ee.Element:
    """
    Build the Earth Engine histogram dictionary representing
    pixel counts for each land-cover class.
    """

    histogram = (
        composite.select("label")
        .reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=aoi,
            scale=scale,
            maxPixels=1e9,
            bestEffort=True,
        )
        .get("label")
    )

    return histogram


def build_valid_coverage(
    image: ee.Image,
    aoi: ee.Geometry,
    scale: int = 10,
) -> ee.Element:
    """
    Estimate the fraction of the AOI containing a valid
    Dynamic World land-cover label (as an EE Element).
    """

    valid_mask = image.select("label").mask().rename("valid")

    coverage = valid_mask.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True,
    ).get("valid")

    return coverage


def format_landcover_distribution(histogram: dict | None) -> dict[str, float]:
    """
    Format the raw histogram dictionary into a percentage-based distribution
    with named classes.
    """
    if not histogram:
        return {}

    total_pixels = sum(histogram.values())
    if total_pixels == 0:
        return {}

    return {
        LAND_COVER_CLASSES[int(class_id)]: (count / total_pixels)
        for class_id, count in histogram.items()
    }


def analyze_landcover(
    aoi: ee.Geometry,
    start_date: str,
    end_date: str,
    scale: int = 10,
) -> AnalysisResult:
    """
    Perform a basic Dynamic World land-cover analysis.
    """

    if not start_date:
        raise ValueError("start_date cannot be empty")

    if not end_date:
        raise ValueError("end_date cannot be empty")

    if scale <= 0:
        raise ValueError("scale must be greater than zero")

    collection, source_image_count_ee = build_landcover_collection(
        aoi=aoi,
        start_date=start_date,
        end_date=end_date,
    )

    # Dynamic World labels are categorical,
    # therefore use mode rather than median.
    composite = collection.select("label").mode()

    histogram_ee = build_landcover_histogram(
        composite=composite,
        aoi=aoi,
        scale=scale,
    )

    coverage_ee = build_valid_coverage(
        image=composite,
        aoi=aoi,
        scale=scale,
    )

    combined_info = ee.Dictionary({
        "source_image_count": source_image_count_ee,
        "histogram": histogram_ee,
        "coverage": coverage_ee
    }).getInfo()

    source_image_count = combined_info.get("source_image_count", 0)

    if source_image_count == 0:
        raise ValueError(
            "No Dynamic World images were found "
            "for the supplied AOI and date range."
        )

    distribution = format_landcover_distribution(
        combined_info.get("histogram")
    )

    coverage_value = combined_info.get("coverage")
    valid_coverage = (
        float(coverage_value) if coverage_value is not None else 0.0
    )

    return AnalysisResult(
        analysis_type="landcover_analysis",
        findings={
            "landcover_distribution": distribution,
            "start_date": start_date,
            "end_date": end_date,
        },
        data_quality=DataQuality(
            source_image_count=source_image_count,
            usable_image_count=source_image_count,
            valid_coverage=valid_coverage,
        ),
        methodology=Methodology(
            dataset=DW_DATASET,
            resolution_m=scale,
            composite_method="mode",
            cloud_masking=(
                "No additional cloud masking applied; "
                "Dynamic World observations used as provided"
            ),
            index="Dynamic World land-cover label",
        ),
        limitations=[
            "Land-cover labels represent the most probable "
            "class for each pixel.",
            "This PoC does not yet use Dynamic World "
            "class probabilities to filter low-confidence pixels.",
            "The mode composite represents the dominant "
            "class over the selected period.",
        ],
        visualizations={},
    )
