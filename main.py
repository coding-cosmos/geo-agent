import ee

from app.gee import initialize_gee
from app.tools.ndvi_tool import ndvi_tool
from app.config import GEE_PROJECT_ID


def main():
    initialize_gee(GEE_PROJECT_ID)

    aoi = ee.Geometry.Rectangle(
        [
            76.80,
            28.35,
            77.20,
            28.65,
        ]
    )

    # ----------------------------------------------
    # Run analysis
    # ----------------------------------------------

    result, validation = ndvi_tool(
        aoi=aoi,
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    print("\n=== NDVI ANALYSIS ===")

    print("\nFindings:")
    print(result.findings)

    print("\nData Quality:")
    print(result.data_quality)

    print("\nMethodology:")
    print(result.methodology)

    print("\nLimitations:")

    for limitation in result.limitations:
        print(f"- {limitation}")

    # ----------------------------------------------
    # Validate analysis
    # ----------------------------------------------

    print("\n=== VALIDATION ===")

    print(f"\nValid: {validation.valid}")

    print(f"Quality Score: " f"{validation.quality_score:.2f}")

    print("\nChecks:")

    for check in validation.checks:
        status = "PASS" if check.passed else "FAIL"

        print(f"[{status}] " f"{check.name}: " f"{check.message}")

    if validation.issues:
        print("\nIssues:")

        for issue in validation.issues:
            print(f"- {issue}")


if __name__ == "__main__":
    main()
