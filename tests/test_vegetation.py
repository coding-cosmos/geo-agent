from unittest.mock import MagicMock, patch
import pytest

from app.analysis.vegetation import analyze_ndvi
from app.models.analysis import AnalysisResult


def test_analyze_ndvi_empty_start_date():
    with pytest.raises(ValueError, match="start_date cannot be empty"):
        analyze_ndvi(
            aoi=MagicMock(),
            start_date="",
            end_date="2025-12-31",
        )


def test_analyze_ndvi_empty_end_date():
    with pytest.raises(ValueError, match="end_date cannot be empty"):
        analyze_ndvi(
            aoi=MagicMock(),
            start_date="2025-01-01",
            end_date="",
        )


def test_analyze_ndvi_invalid_scale():
    with pytest.raises(ValueError, match="scale must be greater than zero"):
        analyze_ndvi(
            aoi=MagicMock(),
            start_date="2025-01-01",
            end_date="2025-12-31",
            scale=0,
        )


def test_analyze_ndvi_invalid_cloud_percentage():
    with pytest.raises(ValueError, match="max_cloud_percentage must be between 0 and 100"):
        analyze_ndvi(
            aoi=MagicMock(),
            start_date="2025-01-01",
            end_date="2025-12-31",
            max_cloud_percentage=-1.0,
        )


@patch("app.analysis.vegetation.ee.Dictionary")
@patch("app.analysis.vegetation.build_ndvi_collection")
def test_analyze_ndvi_no_usable_images(mock_build_ndvi_collection, mock_dictionary):
    mock_build_ndvi_collection.return_value = (MagicMock(), MagicMock())

    mock_dict_instance = MagicMock()
    mock_dict_instance.getInfo.return_value = {"counts": {"source": 10, "usable": 0}, "analysis": None}
    mock_dictionary.return_value = mock_dict_instance

    with pytest.raises(ValueError, match="No usable Sentinel-2 images were found"):
        analyze_ndvi(
            aoi=MagicMock(),
            start_date="2025-01-01",
            end_date="2025-12-31",
        )


@patch("app.analysis.vegetation.ee.Dictionary")
@patch("app.analysis.vegetation.calculate_valid_coverage")
@patch("app.analysis.vegetation.calculate_ndvi_statistics")
@patch("app.analysis.vegetation.build_ndvi_collection")
def test_analyze_ndvi_success(
    mock_build_ndvi_collection,
    mock_calculate_ndvi_statistics,
    mock_calculate_valid_coverage,
    mock_dictionary,
):
    mock_collection = MagicMock()
    mock_build_ndvi_collection.return_value = (mock_collection, MagicMock())
    mock_calculate_ndvi_statistics.return_value = MagicMock()
    mock_calculate_valid_coverage.return_value = MagicMock()

    mock_dict_instance = MagicMock()

    # The .getInfo() call returns a single nested dictionary with counts and analysis
    mock_dict_instance.getInfo.return_value = {
        "counts": {"source": 10, "usable": 5},
        "analysis": {
            "statistics": {"mean": 0.5, "min": 0.1, "max": 0.9, "std_dev": 0.2},
            "valid_coverage": 0.8,
        },
    }
    mock_dictionary.return_value = mock_dict_instance

    result = analyze_ndvi(
        aoi=MagicMock(),
        start_date="2025-01-01",
        end_date="2025-12-31",
    )

    assert isinstance(result, AnalysisResult)
    assert result.analysis_type == "ndvi_analysis"
    assert result.findings["mean_ndvi"] == 0.5
    assert result.findings["minimum_ndvi"] == 0.1
    assert result.findings["maximum_ndvi"] == 0.9
    assert result.findings["ndvi_std_dev"] == 0.2
    assert result.findings["start_date"] == "2025-01-01"
    assert result.findings["end_date"] == "2025-12-31"
    assert result.data_quality.source_image_count == 10
    assert result.data_quality.usable_image_count == 5
    assert result.data_quality.valid_coverage == 0.8
