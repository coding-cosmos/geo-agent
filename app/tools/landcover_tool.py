import ee

from app.analysis.landcover import analyze_landcover
from app.models.analysis import AnalysisResult
from app.models.validation import ValidationResult
from app.validation.validator import validate_analysis_result


def landcover_tool(
    aoi: ee.Geometry,
    start_date: str,
    end_date: str,
    scale: int = 10,
) -> tuple[AnalysisResult, ValidationResult]:
    """
    Agent-facing tool for Dynamic World land-cover analysis.

    Runs the land-cover analysis and validates the resulting
    AnalysisResult before returning it.
    """

    result = analyze_landcover(
        aoi=aoi,
        start_date=start_date,
        end_date=end_date,
        scale=scale,
    )

    validation = validate_analysis_result(result)

    return result, validation
