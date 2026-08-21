import pytest
from unittest.mock import patch, MagicMock
import ee

from app.analysis.landcover import (
    analyze_landcover,
    build_landcover_collection,
    calculate_landcover_distribution,
    calculate_valid_coverage,
    DW_DATASET,
)
from app.models.analysis import AnalysisResult, DataQuality, Methodology


def test_analyze_landcover_empty_start_date():
    mock_aoi = MagicMock(spec=ee.Geometry)
    with pytest.raises(ValueError, match="start_date cannot be empty"):
        analyze_landcover(aoi=mock_aoi, start_date="", end_date="2025-01-01", scale=10)

def test_analyze_landcover_empty_end_date():
    mock_aoi = MagicMock(spec=ee.Geometry)
    with pytest.raises(ValueError, match="end_date cannot be empty"):
        analyze_landcover(aoi=mock_aoi, start_date="2024-01-01", end_date="", scale=10)

def test_analyze_landcover_invalid_scale():
    mock_aoi = MagicMock(spec=ee.Geometry)
    with pytest.raises(ValueError, match="scale must be greater than zero"):
        analyze_landcover(aoi=mock_aoi, start_date="2024-01-01", end_date="2025-01-01", scale=0)
    with pytest.raises(ValueError, match="scale must be greater than zero"):
        analyze_landcover(aoi=mock_aoi, start_date="2024-01-01", end_date="2025-01-01", scale=-5)

@patch('ee.ImageCollection')
def test_build_landcover_collection(mock_image_collection):
    mock_collection_instance = MagicMock()
    mock_filtered_bounds = MagicMock()
    mock_filtered_date = MagicMock()

    mock_image_collection.return_value = mock_collection_instance
    mock_collection_instance.filterBounds.return_value = mock_filtered_bounds
    mock_filtered_bounds.filterDate.return_value = mock_filtered_date
    mock_filtered_date.size.return_value.getInfo.return_value = 42

    aoi = MagicMock(spec=ee.Geometry)
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    collection, count = build_landcover_collection(aoi, start_date, end_date)

    mock_image_collection.assert_called_once_with(DW_DATASET)
    mock_collection_instance.filterBounds.assert_called_once_with(aoi)
    mock_filtered_bounds.filterDate.assert_called_once_with(start_date, end_date)
    assert collection == mock_filtered_date
    assert count == 42

@patch('ee.Reducer.frequencyHistogram')
def test_calculate_landcover_distribution_populated(mock_histogram):
    mock_image = MagicMock(spec=ee.Image)
    mock_aoi = MagicMock(spec=ee.Geometry)
    mock_histogram_reducer = MagicMock()
    mock_histogram.return_value = mock_histogram_reducer

    # 1=trees, 4=crops
    mock_image.select.return_value.reduceRegion.return_value.get.return_value.getInfo.return_value = {
        '1': 300,
        '4': 100
    }

    distribution = calculate_landcover_distribution(mock_image, mock_aoi, 10)

    assert distribution == {'trees': 0.75, 'crops': 0.25}
    mock_image.select.assert_called_with("label")
    mock_image.select.return_value.reduceRegion.assert_called_once_with(
        reducer=mock_histogram_reducer,
        geometry=mock_aoi,
        scale=10,
        maxPixels=1e9,
        bestEffort=True
    )

@patch('ee.Reducer.frequencyHistogram')
def test_calculate_landcover_distribution_empty(mock_histogram):
    mock_image = MagicMock(spec=ee.Image)
    mock_aoi = MagicMock(spec=ee.Geometry)

    mock_image.select.return_value.reduceRegion.return_value.get.return_value.getInfo.return_value = None

    distribution = calculate_landcover_distribution(mock_image, mock_aoi, 10)

    assert distribution == {}

@patch('ee.Reducer.mean')
def test_calculate_valid_coverage(mock_mean):
    mock_image = MagicMock(spec=ee.Image)
    mock_aoi = MagicMock(spec=ee.Geometry)
    mock_mean_reducer = MagicMock()
    mock_mean.return_value = mock_mean_reducer

    mock_image.select.return_value.mask.return_value.rename.return_value.reduceRegion.return_value.get.return_value.getInfo.return_value = 0.85

    coverage = calculate_valid_coverage(mock_image, mock_aoi, 10)

    assert coverage == 0.85
    mock_image.select.assert_called_with("label")
    mock_image.select.return_value.mask.return_value.rename.assert_called_with("valid")

@patch('ee.Reducer.mean')
def test_calculate_valid_coverage_none(mock_mean):
    mock_image = MagicMock(spec=ee.Image)
    mock_aoi = MagicMock(spec=ee.Geometry)

    mock_image.select.return_value.mask.return_value.rename.return_value.reduceRegion.return_value.get.return_value.getInfo.return_value = None

    coverage = calculate_valid_coverage(mock_image, mock_aoi, 10)

    assert coverage == 0.0

@patch('app.analysis.landcover.build_landcover_collection')
def test_analyze_landcover_no_images(mock_build):
    mock_build.return_value = (MagicMock(), 0)
    mock_aoi = MagicMock(spec=ee.Geometry)

    with pytest.raises(ValueError, match="No Dynamic World images were found"):
        analyze_landcover(mock_aoi, "2024-01-01", "2024-12-31", 10)

@patch('app.analysis.landcover.calculate_valid_coverage')
@patch('app.analysis.landcover.calculate_landcover_distribution')
@patch('app.analysis.landcover.build_landcover_collection')
def test_analyze_landcover_happy_path(mock_build, mock_calc_dist, mock_calc_cov):
    mock_collection = MagicMock()
    mock_composite = MagicMock()
    mock_collection.select.return_value.mode.return_value = mock_composite

    mock_build.return_value = (mock_collection, 42)
    mock_calc_dist.return_value = {'trees': 0.8, 'water': 0.2}
    mock_calc_cov.return_value = 0.95

    mock_aoi = MagicMock(spec=ee.Geometry)
    start_date = "2024-01-01"
    end_date = "2024-12-31"
    scale = 10

    result = analyze_landcover(mock_aoi, start_date, end_date, scale)

    mock_build.assert_called_once_with(aoi=mock_aoi, start_date=start_date, end_date=end_date)
    mock_collection.select.assert_called_once_with("label")
    mock_collection.select.return_value.mode.assert_called_once()
    mock_calc_dist.assert_called_once_with(composite=mock_composite, aoi=mock_aoi, scale=scale)
    mock_calc_cov.assert_called_once_with(image=mock_composite, aoi=mock_aoi, scale=scale)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_type == "landcover_analysis"
    assert result.findings["landcover_distribution"] == {'trees': 0.8, 'water': 0.2}
    assert result.findings["start_date"] == start_date
    assert result.findings["end_date"] == end_date

    assert isinstance(result.data_quality, DataQuality)
    assert result.data_quality.source_image_count == 42
    assert result.data_quality.usable_image_count == 42
    assert result.data_quality.valid_coverage == 0.95

    assert isinstance(result.methodology, Methodology)
    assert result.methodology.dataset == DW_DATASET
    assert result.methodology.resolution_m == scale
    assert result.methodology.composite_method == "mode"
