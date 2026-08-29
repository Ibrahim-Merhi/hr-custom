from unittest import TestCase
from hr_custom.attendance.geofence import get_distance_in_meters, validate_coordinates
class TestGeofence(TestCase):
    def test_same_point(self):
        self.assertAlmostEqual(get_distance_in_meters(24.7136, 46.6753, 24.7136, 46.6753), 0, places=5)
    def test_known_hundred_meters(self):
        self.assertTrue(95 < get_distance_in_meters(0, 0, 0, 0.0009) < 105)
    def test_coordinate_ranges(self):
        with self.assertRaises(ValueError): validate_coordinates(91, 0)
        with self.assertRaises(ValueError): validate_coordinates(0, 181)
