import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from hr_custom.services import simple_leave
from hr_custom.setup.leave_application_layout import PREFERRED_FIELD_ORDER


class TestLeaveApplicationDefaults(unittest.TestCase):
    def test_first_company_details_row_is_used(self):
        def exists(doctype, name):
            return doctype == "DocType" and name == "Employee Branch Assignment"

        def get_value(doctype, filters, fieldname=None, **kwargs):
            if doctype == "Employee Branch Assignment":
                self.assertEqual(kwargs.get("order_by"), "idx asc")
                return "First Company"
            if doctype == "Employee":
                return "Fallback Company"
            return None

        database = SimpleNamespace(exists=exists, get_value=get_value)
        with patch.object(simple_leave.frappe, "db", database):
            self.assertEqual(
                simple_leave.get_employee_primary_company("HR-EMP-00062"),
                "First Company",
            )

    def test_employee_company_is_fallback_without_company_details(self):
        database = SimpleNamespace(
            exists=lambda doctype, name: False,
            get_value=lambda doctype, employee, fieldname=None, **kwargs: "Employee Company",
        )
        with patch.object(simple_leave.frappe, "db", database):
            self.assertEqual(
                simple_leave.get_employee_primary_company("HR-EMP-00062"),
                "Employee Company",
            )

    def test_first_workflow_approver_linked_user_fills_hrms_field(self):
        def get_value(doctype, filters, fieldname=None, **kwargs):
            if doctype == "Employee" and fieldname == "user_id":
                return "approver@example.com"
            if doctype == "User" and fieldname == "enabled":
                return 1
            return None

        database = SimpleNamespace(
            get_value=get_value,
        )
        with (
            patch.object(simple_leave.frappe, "db", database),
            patch.object(simple_leave, "get_employee_approvers", return_value=["HR-EMP-APPROVER"]),
        ):
            self.assertEqual(
                simple_leave.get_standard_leave_approver("HR-EMP-00062"),
                "approver@example.com",
            )

    def test_leave_layout_keeps_reason_in_dates_section(self):
        self.assertLess(PREFERRED_FIELD_ORDER.index("section_break_5"), PREFERRED_FIELD_ORDER.index("description"))
        self.assertLess(PREFERRED_FIELD_ORDER.index("description"), PREFERRED_FIELD_ORDER.index("custom_hourly_leave_section"))
        self.assertEqual(
            PREFERRED_FIELD_ORDER[PREFERRED_FIELD_ORDER.index("from_date") + 1],
            "column_break1",
        )
        self.assertEqual(
            PREFERRED_FIELD_ORDER[PREFERRED_FIELD_ORDER.index("column_break1") + 1],
            "to_date",
        )


class TestPendingLeaveWithdrawal(unittest.TestCase):
    def _pending_request(self, **values):
        request = frappe._dict(
            employee="HR-EMP-00062",
            docstatus=0,
            status="Open",
            custom_approval_stage="Pending Approver Approval",
        )
        request.update(values)
        return request

    def test_employee_can_withdraw_own_pending_request(self):
        simple_leave.validate_pending_leave_withdrawal(
            self._pending_request(), "HR-EMP-00062"
        )

    def test_employee_cannot_withdraw_another_employees_request(self):
        with (
            patch.object(simple_leave, "_", side_effect=lambda message: message),
            patch.object(simple_leave.frappe, "throw", side_effect=frappe.PermissionError),
        ):
            with self.assertRaises(frappe.PermissionError):
                simple_leave.validate_pending_leave_withdrawal(
                    self._pending_request(), "HR-EMP-00999"
                )

    def test_employee_can_edit_own_request_waiting_for_approver(self):
        simple_leave.validate_pending_leave_edit(
            self._pending_request(), "HR-EMP-00062"
        )

    def test_request_waiting_for_hr_cannot_be_edited(self):
        with (
            patch.object(simple_leave, "_", side_effect=lambda message: message),
            patch.object(simple_leave.frappe, "throw", side_effect=frappe.ValidationError),
        ):
            with self.assertRaises(frappe.ValidationError):
                simple_leave.validate_pending_leave_edit(
                    self._pending_request(custom_approval_stage="Pending HR Approval"),
                    "HR-EMP-00062",
                )

    def test_approved_request_cannot_be_withdrawn(self):
        with (
            patch.object(simple_leave, "_", side_effect=lambda message: message),
            patch.object(simple_leave.frappe, "throw", side_effect=frappe.ValidationError),
        ):
            with self.assertRaises(frappe.ValidationError):
                simple_leave.validate_pending_leave_withdrawal(
                    self._pending_request(
                        docstatus=1,
                        status="Approved",
                        custom_approval_stage="Approved",
                    ),
                    "HR-EMP-00062",
                )


if __name__ == "__main__":
    unittest.main()
