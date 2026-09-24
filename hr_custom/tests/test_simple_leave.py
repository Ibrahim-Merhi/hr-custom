from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hr_custom.services.simple_leave import calculate_leave_calendar, get_available_leave_types, get_employee_approvers, process_leave_approval, submit_simple_leave


class TestSimpleLeave(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.user = "simple.leave.test@example.com"
        self.employee = make_employee(self.user, company="_Test Company")
        self.leave_type = "_Test Simple Mobile Leave"
        self.hour_leave_type = "_Test Simple Mobile Hour Leave"
        self.employment_type = "_Test Simple Mobile Both"
        if not frappe.db.exists("Employment Type", self.employment_type):
            frappe.get_doc({"doctype": "Employment Type", "employee_type_name": self.employment_type, "custom_leave_calculation_mode": "Both"}).insert()
        else:
            frappe.db.set_value("Employment Type", self.employment_type, "custom_leave_calculation_mode", "Both")
        frappe.db.set_value("Employee", self.employee, "employment_type", self.employment_type)
        if not frappe.db.exists("Leave Type", self.leave_type):
            frappe.get_doc({"doctype": "Leave Type", "leave_type_name": self.leave_type, "custom_leave_unit": "Days", "include_holiday": 0}).insert()
        if not frappe.db.exists("Leave Type", self.hour_leave_type):
            frappe.get_doc({"doctype": "Leave Type", "leave_type_name": self.hour_leave_type, "custom_leave_unit": "Hours", "include_holiday": 0}).insert()
        frappe.db.delete("Leave Allocation", {"employee": self.employee, "leave_type": self.leave_type})
        frappe.get_doc({"doctype": "Leave Allocation", "employee": self.employee, "leave_type": self.leave_type, "from_date": "2028-01-01", "to_date": "2028-12-31", "new_leaves_allocated": 20}).insert().submit()
        frappe.db.delete("Leave Allocation", {"employee": self.employee, "leave_type": self.hour_leave_type})
        frappe.get_doc({"doctype": "Leave Allocation", "employee": self.employee, "leave_type": self.hour_leave_type, "from_date": "2028-01-01", "to_date": "2028-12-31", "new_leaves_allocated": 40}).insert().submit()
        employee = frappe.get_doc("Employee", self.employee)
        employee.employment_type = self.employment_type
        employee.custom_default_mobile_leave_type = self.leave_type
        employee.custom_use_custom_work_schedule = 1
        employee.set("custom_weekly_working_hours", [])
        for index, day in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"), 1):
            employee.append("custom_weekly_working_hours", {"day_of_week": day, "working_hours": 8 if day not in ("Friday", "Saturday") else 0, "sequence": index, "enabled": 1})
        employee.set("custom_leave_approvers", [])
        employee.append("custom_leave_approvers", {"approver": self.employee, "sequence": 1, "enabled": 1})
        employee.save()
        frappe.set_user(self.user)

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def test_dates_reason_select_allocation_and_approver(self):
        result = submit_simple_leave("2028-02-06", "2028-02-07", "Family appointment")
        application = frappe.get_doc("Leave Application", result["name"])
        self.assertEqual(application.leave_type, self.leave_type)
        self.assertEqual(application.leave_approver, self.user)
        self.assertEqual(application.description, "Family appointment")
        self.assertEqual(result["approver_count"], 1)
        self.assertEqual(result["leave_days"], 2)
        self.assertEqual(application.custom_approval_stage, "Pending Approver Approval")
        self.assertEqual(application.custom_current_approver, self.employee)
        self.assertEqual(application.custom_approval_steps[0].status, "Pending")

    def test_approver_then_hr_manager_finally_submits(self):
        result = submit_simple_leave("2028-03-06", "2028-03-07", "Sequential approval")
        frappe.set_user(self.user)
        first = process_leave_approval(result["name"], "approve", "Approver accepted")
        self.assertEqual(first["stage"], "Pending HR Approval")
        self.assertEqual(first["docstatus"], 0)
        frappe.set_user("Administrator")
        final = process_leave_approval(result["name"], "approve", "HR accepted")
        self.assertEqual(final["stage"], "Approved")
        self.assertEqual(final["status"], "Approved")
        self.assertEqual(final["docstatus"], 1)

    def test_calendar_uses_employee_weekend_and_returns_next_working_day(self):
        result = calculate_leave_calendar(self.employee, self.leave_type, "2026-09-10", "2026-09-12")
        self.assertEqual(result["calendar_days"], 3)
        self.assertEqual(result["leave_days"], 1)
        self.assertEqual(str(result["return_to_work_date"]), "2026-09-14")

    def test_half_day_request_uses_standard_leave_fields(self):
        with patch("hr_custom.api.mobile_attendance._employee_for_user", return_value=frappe._dict(name=self.employee)):
            result = submit_simple_leave("2028-02-08", "2028-02-08", "Half-day appointment", leave_type=self.leave_type, half_day=1)
        application = frappe.get_doc("Leave Application", result["name"])
        self.assertEqual(result["leave_days"], 0.5)
        self.assertEqual(application.half_day, 1)
        self.assertEqual(str(application.half_day_date), "2028-02-08")
        self.assertEqual(application.total_leave_days, 0.5)

    def test_partial_hour_request_uses_hour_allocation(self):
        result = submit_simple_leave("2028-02-08", "2028-02-08", "Appointment", "Hours", "Partial Hours", 2)
        application = frappe.get_doc("Leave Application", result["name"])
        self.assertEqual(application.leave_type, self.hour_leave_type)
        self.assertEqual(application.custom_leave_unit, "Hours")
        self.assertEqual(application.custom_leave_hours, 2)
        self.assertEqual(result["leave_hours"], 2)

    def test_employee_can_choose_an_allocated_leave_type(self):
        choices = get_available_leave_types("2028-02-08", "2028-02-08")
        self.assertEqual({row["leave_type"] for row in choices["leave_types"]}, {self.leave_type, self.hour_leave_type})
        result = submit_simple_leave("2028-02-08", "2028-02-08", "Chosen type", leave_type=self.hour_leave_type, leave_duration="Partial Hours", partial_hours=2)
        self.assertEqual(result["leave_type"], self.hour_leave_type)

    def test_employee_primary_approver_is_synchronized(self):
        self.assertEqual(get_employee_approvers(self.employee), [self.employee])
        self.assertEqual(frappe.db.get_value("Employee", self.employee, "leave_approver"), self.user)

    def test_reason_and_date_validation(self):
        with self.assertRaises(frappe.ValidationError):
            submit_simple_leave("2028-02-08", "2028-02-07", "Wrong dates")
        with self.assertRaises(frappe.ValidationError):
            submit_simple_leave("2028-02-06", "2028-02-07", "")
