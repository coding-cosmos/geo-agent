import ee
from app.config import GEE_PROJECT_ID

def initialize_gee(project_id: str) -> None:
    """
    Initialize the Google Earth Engine Python API.

    Args:
        project_id: Google Cloud project ID registered for Earth Engine.
    """
    try:
        ee.Initialize(project=project_id)
    except Exception as e:
        raise RuntimeError(
            "Failed to initialize Earth Engine. "
            "In a server environment, ensure the default service account has Earth Engine access, "
            "or set GOOGLE_APPLICATION_CREDENTIALS pointing to a valid service account key. "
            "For local development, run `earthengine authenticate`."
        ) from e

if __name__ == "__main__":
    initialize_gee(GEE_PROJECT_ID)

    result = ee.String("Hello Earth Engine").getInfo()

    print(result)
