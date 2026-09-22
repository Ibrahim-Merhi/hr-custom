import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee
from hrms.hr.doctype.leave_application.leave_application import OverlapError

from hr_custom.overrides.leave_application import HourlyLeaveApplication
from hr_custom.api.hourly_leave import get_hourly_leave_preview
from hr_custom.hr_custom.report.hourly_leave_balance.hourly_leave_balance import execute as hourly_balance_report
from hr_custom.services.hourly_leave import (
    calculate_hourly_leave,
    get_hour_leave_balance,
)


class TestHourlyLeave(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.employee = make_employee("hourly.leave.test@example.com", company="_Test Company")
        self.employment_type = self._make_employment_type("Hours", {"Monday": 5, "Tuesday": 6, "Wednesday": 4, "Thursday": 6, "Friday": 3, "Saturday": 0, "Sunday": 0})
        employee = frappe.get_doc("Employee", self.employee)
        employee.employment_type = self.employment_type
        employee.custom_use_custom_work_schedule = 0
        employee.holiday_list = self._make_holiday_list()
        employee.save()
        self.leave_type = self._make_leave_type("Hours")
        self._allocate(self.leave_type, 80)

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _make_employment_type(self, mode, schedule, suffix=""):
        name = f"_Test Hourly Employment{suffix}"
        frappe.db.delete("Employment Type Working Hours", {"parent": name})
        frappe.db.delete("Employment Type", name)
        doc = frappe.get_doc({"doctype": "Employment Type", "employee_type_name": name, "custom_leave_calculation_mode": mode})
        for day, hours in schedule.items():
            doc.append("custom_weekly_working_hours", {"day_of_week": day, "working_hours": hours, "enabled": 1})
        return doc.insert().name

    def _make_leave_type(self, unit, suffix=""):
        name = f"_Test Annual Leave {unit}{suffix}"
        frappe.db.delete("Leave Type", name)
        return frappe.get_doc({"doctype": "Leave Type", "leave_type_name": name, "custom_leave_unit": unit, "include_holiday": 0}).insert().name

    def _make_holiday_list(self):
        name = "_Test Hourly Empty Holidays"
        frappe.db.delete("Holiday", {"parent": name})
        frappe.db.delete("Holiday List", name)
        return frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": name, "from_date": "2027-01-01", "to_date": "2027-12-31"}).insert().name

    def _allocate(self, leave_type, hours):
        return frappe.get_doc({
            "doctype": "Leave Allocation", "employee": self.employee, "leave_type": leave_type,
            "from_date": "2027-01-01", "to_date": "2027-12-31", "new_leaves_allocated": hours,
        }).insert().submit()

    def _application(self, start, end=None, duration="Full Scheduled Hours", partial=None, status="Open"):
        return frappe.get_doc({
            "doctype": "Leave Application", "employee": self.employee, "leave_type": self.leave_type,
            "from_date": start, "to_date": end or start, "posting_date": "2027-01-01",
            "status": status, "custom_leave_duration": duration, "custom_partial_hours": partial,
            "description": "Hourly leave test",
        })

    def test_override_is_active(self):
        self.assertIsInstance(self._application("2027-01-05"), HourlyLeaveApplication)

    def test_one_day_and_multi_day_schedule(self):
        one = calculate_hourly_leave(self.employee, self.leave_type, "2027-01-05", "2027-01-05")
        self.assertEqual(one["total_leave_hours"], 6)
        multi = calculate_hourly_leave(self.employee, self.leave_type, "2027-01-04", "2027-01-06")
        self.assertEqual(multi["total_leave_hours"], 15)
        self.assertEqual(len(multi["details"]), 3)

    def test_non_working_day_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            calculate_hourly_leave(self.employee, self.leave_type, "2027-01-10", "2027-01-10")

    def test_holiday_has_zero_deduction(self):
        holiday_list = frappe.get_doc("Holiday List", "_Test Hourly Empty Holidays")
        holiday_list.append("holidays", {"holiday_date": "2027-01-05", "description": "Test Holiday"})
        holiday_list.save()
        with self.assertRaises(frappe.ValidationError):
            calculate_hourly_leave(self.employee, self.leave_type, "2027-01-05", "2027-01-05")
        result = calculate_hourly_leave(self.employee, self.leave_type, "2027-01-04", "2027-01-05")
        self.assertEqual(result["total_leave_hours"], 5)
        self.assertEqual(result["details"][1]["is_holiday"], 1)
        self.assertEqual(result["details"][1]["leave_hours"], 0)

    def test_partial_hours_and_limit(self):
        result = calculate_hourly_leave(self.employee, self.leave_type, "2027-01-08", "2027-01-08", "Partial Hours", 2)
        self.assertEqual(result["total_scheduled_hours"], 3)
        self.assertEqual(result["total_leave_hours"], 2)
        with self.assertRaises(frappe.ValidationError):
            calculate_hourly_leave(self.employee, self.leave_type, "2027-01-08", "2027-01-08", "Partial Hours", 4)
        with self.assertRaises(frappe.ValidationError):
            calculate_hourly_leave(self.employee, self.leave_type, "2027-01-08", "2027-01-09", "Partial Hours", 2)

    def test_employee_override_and_fallback(self):
        employee = frappe.get_doc("Employee", self.employee)
        employee.custom_use_custom_work_schedule = 1
        employee.set("custom_weekly_working_hours", [])
        employee.append("custom_weekly_working_hours", {"day_of_week": "Tuesday", "working_hours": 4, "enabled": 1})
        employee.save()
        result = calculate_hourly_leave(self.employee, self.leave_type, "2027-01-05", "2027-01-05")
        self.assertEqual(result["total_leave_hours"], 4)
        self.assertEqual(result["schedule_source"], "Employee")
        employee.custom_use_custom_work_schedule = 0
        employee.save()
        self.assertEqual(calculate_hourly_leave(self.employee, self.leave_type, "2027-01-05", "2027-01-05")["total_leave_hours"], 6)

    def test_missing_schedule_and_duplicate_validation(self):
        empty_type = self._make_employment_type("Hours", {}, " Empty")
        frappe.db.set_value("Employee", self.employee, "employment_type", empty_type)
        with self.assertRaises(frappe.ValidationError):
            calculate_hourly_leave(self.employee, self.leave_type, "2027-01-05", "2027-01-05")
        doc = frappe.get_doc("Employment Type", empty_type)
        doc.append("custom_weekly_working_hours", {"day_of_week": "Monday", "working_hours": 4, "enabled": 1})
        doc.append("custom_weekly_working_hours", {"day_of_week": "Monday", "working_hours": 5, "enabled": 1})
        with self.assertRaises(frappe.ValidationError):
            doc.save()

    def test_decimal_precision(self):
        employment_type = frappe.get_doc("Employment Type", self.employment_type)
        next(row for row in employment_type.custom_weekly_working_hours if row.day_of_week == "Monday").working_hours = 4.5
        employment_type.save()
        result = calculate_hourly_leave(self.employee, self.leave_type, "2027-01-04", "2027-01-04")
        self.assertEqual(result["total_leave_hours"], 4.5)

    def test_balance_submit_and_cancel(self):
        app = self._application("2027-01-05", status="Approved").insert().submit()
        self.assertEqual(app.custom_leave_hours, 6)
        self.assertEqual(get_hour_leave_balance(self.employee, self.leave_type, "2027-01-05")["remaining_hours"], 74)
        ledger_hours = frappe.db.get_value("Leave Ledger Entry", {"transaction_name": app.name, "docstatus": 1}, "leaves")
        self.assertEqual(flt(ledger_hours), -6)
        app.cancel()
        self.assertEqual(get_hour_leave_balance(self.employee, self.leave_type, "2027-01-05")["remaining_hours"], 80)

    def test_insufficient_exact_and_overlap(self):
        frappe.db.set_value("Leave Allocation", {"employee": self.employee, "leave_type": self.leave_type}, "total_leaves_allocated", 6)
        exact = self._application("2027-01-05", status="Approved").insert().submit()
        self.assertEqual(get_hour_leave_balance(self.employee, self.leave_type, "2027-01-05")["remaining_hours"], 0)
        with self.assertRaises(frappe.ValidationError):
            self._application("2027-01-05").insert()
        exact.cancel()
        with self.assertRaises(frappe.ValidationError):
            self._application("2027-01-04", "2027-01-05").insert()

    def test_insufficient_balance_and_overlap_are_independent(self):
        frappe.db.set_value("Leave Allocation", {"employee": self.employee, "leave_type": self.leave_type}, "total_leaves_allocated", 5)
        with self.assertRaises(frappe.ValidationError):
            self._application("2027-01-05").insert()
        frappe.db.set_value("Leave Allocation", {"employee": self.employee, "leave_type": self.leave_type}, "total_leaves_allocated", 80)
        self._application("2027-01-05", status="Approved").insert().submit()
        with self.assertRaises(OverlapError):
            self._application("2027-01-05").insert()

    def test_employment_type_unit_eligibility(self):
        frappe.db.set_value("Employment Type", self.employment_type, "custom_leave_calculation_mode", "Days")
        with self.assertRaises(frappe.ValidationError):
            self._application("2027-01-05").insert()

    def test_day_leave_uses_standard_hrms(self):
        day_type = self._make_leave_type("Days", " Regression")
        frappe.db.set_value("Employment Type", self.employment_type, "custom_leave_calculation_mode", "Both")
        self._allocate(day_type, 5)
        app = frappe.get_doc({
            "doctype": "Leave Application", "employee": self.employee, "leave_type": day_type,
            "from_date": "2027-01-04", "to_date": "2027-01-04", "posting_date": "2027-01-01",
            "status": "Open", "description": "Day leave regression",
        }).insert()
        self.assertEqual(app.custom_leave_unit, "Days")
        self.assertEqual(app.total_leave_days, 1)

    def test_complete_business_acceptance_scenario(self):
        full = self._application("2027-01-05", "2027-01-06", status="Approved").insert().submit()
        self.assertEqual(full.custom_leave_hours, 10)
        self.assertEqual(get_hour_leave_balance(self.employee, self.leave_type, "2027-01-05")["remaining_hours"], 70)

        partial = self._application("2027-01-08", duration="Partial Hours", partial=2, status="Approved").insert().submit()
        self.assertEqual(partial.custom_scheduled_hours, 3)
        self.assertEqual(partial.custom_leave_hours, 2)
        self.assertEqual(get_hour_leave_balance(self.employee, self.leave_type, "2027-01-08")["remaining_hours"], 68)

        partial.cancel()
        self.assertEqual(get_hour_leave_balance(self.employee, self.leave_type, "2027-01-08")["remaining_hours"], 70)
        full.cancel()
        self.assertEqual(get_hour_leave_balance(self.employee, self.leave_type, "2027-01-05")["remaining_hours"], 80)

    def test_preview_api_employee_scope(self):
        frappe.set_user("hourly.leave.test@example.com")
        result = get_hourly_leave_preview(self.employee, self.leave_type, "2027-01-05", "2027-01-06")
        self.assertEqual(result["total_leave_hours"], 10)
        frappe.set_user("Administrator")
        other_employee = make_employee("hourly.leave.other@example.com", company="_Test Company")
        frappe.set_user("hourly.leave.test@example.com")
        with self.assertRaises(frappe.PermissionError):
            get_hourly_leave_preview(other_employee, self.leave_type, "2027-01-05", "2027-01-06")

    def test_hourly_balance_report(self):
        self._application("2027-01-05", status="Approved").insert().submit()
        columns, rows = hourly_balance_report({"as_of_date": "2027-01-05", "employee": self.employee})
        self.assertTrue(columns)
        row = next(row for row in rows if row.leave_type == self.leave_type)
        self.assertEqual(row.allocated_hours, 80)
        self.assertEqual(row.used_hours, 6)
        self.assertEqual(row.remaining_hours, 74)
