import ee

from app.analysis.vegetation import analyze_ndvi
from app.models.analysis import AnalysisResult
from app.models.validation import ValidationResult
from app.validation.validator import validate_analysis_result


def ndvi_tool(
    aoi: ee.Geometry,
    start_date: str,
    end_date: str,
    max_cloud_percentage: float = 20.0,
    scale: int = 10,
) -> tuple[AnalysisResult, ValidationResult]:
    """
    Agent-facing tool for NDVI analysis.

    Runs the NDVI analysis and validates the resulting
    AnalysisResult before returning it.
    """

    result = analyze_ndvi(
        aoi=aoi,
        start_date=start_date,
        end_date=end_date,
        max_cloud_percentage=max_cloud_percentage,
        scale=scale,
    )

    validation = validate_analysis_result(result)

    return result, validation
