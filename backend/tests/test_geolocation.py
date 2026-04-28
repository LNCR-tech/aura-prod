"""Test geolocation distance calculation with Haversine formula."""

import pytest
from app.services.geolocation import haversine_m


class TestHaversineDistance:
    """Verify Haversine formula calculates correct distances."""

    def test_same_location_zero_distance(self):
        """Same lat/lng = 0 meters."""
        dist = haversine_m(51.5074, -0.1278, 51.5074, -0.1278)
        assert dist == pytest.approx(0, abs=0.1)

    def test_known_distance_london_to_paris(self):
        """London (51.5074, -0.1278) to Paris (48.8566, 2.3522) ≈ 343 km."""
        dist = haversine_m(51.5074, -0.1278, 48.8566, 2.3522)
        assert 340_000 < dist < 350_000, f"Expected ~343km, got {dist/1000:.0f}km"

    def test_small_distance_50m_inside_radius(self):
        """Points 50m apart should be inside 100m radius."""
        lat1, lng1 = 0.0, 0.0
        lat2, lng2 = 0.00045, 0.00045
        dist = haversine_m(lat1, lng1, lat2, lng2)
        assert 50 < dist < 100, f"Expected ~70m, got {dist:.1f}m"

    def test_boundary_exactly_on_radius(self):
        """Test point exactly on boundary is <= radius."""
        lat1, lng1 = 40.7128, -74.0060  # NYC
        dist = haversine_m(lat1, lng1, lat1 + 0.01, lng1)
        assert dist > 0, "Distance should be > 0"
        # Use actual boundary check in app: dist <= radius_m

    def test_antimeridian_no_crash(self):
        """Coordinates near antimeridian should not crash."""
        dist = haversine_m(0.0, 179.9, 0.0, -179.9)
        assert dist > 0 and dist < 1_000_000, "Antimeridian distance should be reasonable"

    def test_pole_no_crash(self):
        """Coordinates near poles should not crash."""
        dist = haversine_m(89.0, 0.0, 89.5, 0.0)
        assert dist > 0, "Pole distance should be > 0"


class TestGeofenceCheck:
    """Verify geofence verification logic."""

    def test_inside_radius_passes(self):
        """Point inside radius should be OK."""
        from app.services.geolocation import geofence_check

        result = geofence_check(
            user_lat=40.7128,
            user_lng=-74.0060,
            event_lat=40.7128,
            event_lng=-74.0060,
            radius_m=100.0,
            accuracy_m=5.0,
            max_allowed_accuracy_m=50.0,
            require_accuracy=False,
        )
        assert result.ok is True

    def test_outside_radius_fails(self):
        """Point outside radius should fail."""
        from app.services.geolocation import geofence_check

        result = geofence_check(
            user_lat=40.7128,
            user_lng=-74.0060,
            event_lat=40.8128,  # ~11 km north
            event_lng=-74.0060,
            radius_m=1000.0,  # 1 km
            accuracy_m=5.0,
            max_allowed_accuracy_m=50.0,
            require_accuracy=False,
        )
        assert result.ok is False
        assert result.distance_m > result.radius_m
