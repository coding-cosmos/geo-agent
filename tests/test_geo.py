from unittest.mock import patch
import app.agent.geo as geo


def test_geojson_to_ee_geometry_mock():
    """Test that geojson_to_ee_geometry calls ee.Geometry with the provided geojson."""
    geojson = {
        "type": "Point",
        "coordinates": [125.6, 10.1]
    }

    with patch("app.agent.geo.ee.Geometry") as mock_geometry:
        mock_geometry.return_value = "mock_ee_geometry"

        result = geo.geojson_to_ee_geometry(geojson)

        assert result == "mock_ee_geometry"
        mock_geometry.assert_called_once_with(geojson)

def test_geojson_to_ee_geometry_polygon():
    """Test with a Polygon geometry."""
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]]
        ]
    }

    with patch("app.agent.geo.ee.Geometry") as mock_geometry:
        mock_geometry.return_value = "mock_ee_geometry_polygon"

        result = geo.geojson_to_ee_geometry(geojson)

        assert result == "mock_ee_geometry_polygon"
        mock_geometry.assert_called_once_with(geojson)
