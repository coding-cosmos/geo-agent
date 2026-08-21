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
) -> tuple[ee.ImageCollection, int]:
    """
    Build a Dynamic World collection filtered
    by AOI and date.

    Returns:
        collection:
            Dynamic World images for the AOI and period.

        source_image_count:
            Number of source images found.
    """

    collection = (
        ee.ImageCollection(DW_DATASET)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
    )

    source_image_count = collection.size().getInfo()

    return collection, source_image_count


def calculate_landcover_distribution(
    composite: ee.Image,
    aoi: ee.Geometry,
    scale: int = 10,
) -> dict[str, float]:
    """
    Calculate the percentage of the AOI belonging
    to each Dynamic World land-cover class.
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
        .getInfo()
    )

    if not histogram:
        return {}

    total_pixels = sum(histogram.values())

    return {
        LAND_COVER_CLASSES[int(class_id)]: (count / total_pixels)
        for class_id, count in histogram.items()
    }


def calculate_valid_coverage(
    image: ee.Image,
    aoi: ee.Geometry,
    scale: int = 10,
) -> float:
    """
    Estimate the fraction of the AOI containing a valid
    Dynamic World land-cover label.
    """

    valid_mask = image.select("label").mask().rename("valid")

    coverage = valid_mask.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True,
    ).get("valid")

    coverage_value = coverage.getInfo()

    if coverage_value is None:
        return 0.0

    return float(coverage_value)


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

    collection, source_image_count = build_landcover_collection(
        aoi=aoi,
        start_date=start_date,
        end_date=end_date,
    )

    if source_image_count == 0:
        raise ValueError(
            "No Dynamic World images were found " "for the supplied AOI and date range."
        )

    # Dynamic World labels are categorical,
    # therefore use mode rather than median.
    composite = collection.select("label").mode()

    distribution = calculate_landcover_distribution(
        composite=composite,
        aoi=aoi,
        scale=scale,
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
            valid_coverage=calculate_valid_coverage(
                image=composite,
                aoi=aoi,
                scale=scale,
            ),
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
            "Land-cover labels represent the most probable " "class for each pixel.",
            "This PoC does not yet use Dynamic World "
            "class probabilities to filter low-confidence pixels.",
            "The mode composite represents the dominant "
            "class over the selected period.",
        ],
        visualizations={},
    )
