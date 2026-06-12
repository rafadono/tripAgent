import unittest

try:
    from pydantic import ValidationError
    from tripagent.models import DayIn, LocationIn
except Exception as exc:  # pragma: no cover
    ValidationError = Exception
    DayIn = None
    LocationIn = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(DayIn is None, f"Missing dependency: {_IMPORT_ERROR}")
class DayInValidationTests(unittest.TestCase):
    def test_valid_day(self):
        day = DayIn(
            date="2026-02-28",
            day_start_time="08:30",
            day_end_time="18:30",
            start_location=LocationIn(lat=-33.45, lng=-70.66),
            pois=[],
        )
        self.assertEqual(day.date, "2026-02-28")

    def test_invalid_date(self):
        with self.assertRaises(ValidationError):
            DayIn(
                date="28-02-2026",
                day_start_time="08:30",
                day_end_time="18:30",
                start_location=LocationIn(lat=-33.45, lng=-70.66),
                pois=[],
            )

    def test_invalid_time(self):
        with self.assertRaises(ValidationError):
            DayIn(
                date="2026-02-28",
                day_start_time="8:30",
                day_end_time="18:30",
                start_location=LocationIn(lat=-33.45, lng=-70.66),
                pois=[],
            )


if __name__ == "__main__":
    unittest.main()
