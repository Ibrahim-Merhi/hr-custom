import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from hr_custom.services import attendance_correction, portal_identity


class TestPortalDocumentSystemUser(unittest.TestCase):
    def test_virtual_portal_user_is_switched_and_restored(self):
        session = frappe._dict(user="portal::HR-EMP-00062")
        local = frappe._dict(form_dict=frappe._dict(employee="HR-EMP-00062"))
        original_form_dict = local.form_dict

        def set_user(user):
            session.user = user

        with (
            patch.object(portal_identity.frappe, "session", session),
            patch.object(portal_identity.frappe, "local", local),
            patch.object(portal_identity.frappe, "set_user", side_effect=set_user),
        ):
            with portal_identity.run_portal_document_as_system_user():
                self.assertEqual(session.user, "Administrator")
                self.assertIs(local.form_dict, original_form_dict)

            self.assertEqual(session.user, "portal::HR-EMP-00062")
            self.assertIs(local.form_dict, original_form_dict)

    def test_real_user_is_not_switched(self):
        session = frappe._dict(user="hr.manager@example.com")
        with (
            patch.object(portal_identity.frappe, "session", session),
            patch.object(portal_identity.frappe, "set_user") as set_user,
        ):
            with portal_identity.run_portal_document_as_system_user():
                self.assertEqual(session.user, "hr.manager@example.com")
            set_user.assert_not_called()


class TestAttendanceCorrectionAdjustments(unittest.TestCase):
    def _request(self):
        class Request:
            attendance_date = date(2026, 10, 8)

            def set(self, fieldname, value):
                setattr(self, fieldname, value)

        return Request()

    def test_hr_can_adjust_values_on_attendance_date(self):
        doc = self._request()
        with patch.object(attendance_correction, "_is_hr_manager", return_value=True):
            attendance_correction._apply_hr_adjustments(
                doc,
                "2026-10-08 08:30:00",
                "2026-10-08 17:15:00",
            )

        self.assertEqual(doc.requested_check_in_time, datetime(2026, 10, 8, 8, 30))
        self.assertEqual(doc.requested_check_out_time, datetime(2026, 10, 8, 17, 15))

    def test_non_hr_cannot_adjust_values(self):
        doc = self._request()
        with (
            patch.object(attendance_correction, "_is_hr_manager", return_value=False),
            patch.object(attendance_correction, "_", side_effect=lambda message: message),
            patch.object(attendance_correction.frappe, "throw", side_effect=frappe.PermissionError),
        ):
            with self.assertRaises(frappe.PermissionError):
                attendance_correction._apply_hr_adjustments(doc, "2026-10-08 08:30:00")

    def test_adjustment_must_match_attendance_date(self):
        doc = self._request()
        with (
            patch.object(attendance_correction, "_is_hr_manager", return_value=True),
            patch.object(attendance_correction, "_", side_effect=lambda message: message),
            patch.object(attendance_correction.frappe, "throw", side_effect=frappe.ValidationError),
        ):
            with self.assertRaises(frappe.ValidationError):
                attendance_correction._apply_hr_adjustments(doc, "2026-10-09 08:30:00")


class TestAttendanceCorrectionRouting(unittest.TestCase):
    def test_new_request_notification_is_queued_after_commit(self):
        doc = frappe._dict(name="ACR-TEST-00001")
        with patch.object(attendance_correction.frappe, "enqueue") as enqueue:
            attendance_correction.enqueue_reviewer_notification(doc)

        enqueue.assert_called_once_with(
            "hr_custom.services.attendance_correction.notify_current_reviewer_by_name",
            queue="short",
            enqueue_after_commit=True,
            job_id="attendance-correction-notify-ACR-TEST-00001",
            request_name="ACR-TEST-00001",
        )

    def test_missing_request_notification_job_exits_cleanly(self):
        database = SimpleNamespace(exists=lambda *args, **kwargs: False)
        with (
            patch.object(attendance_correction.frappe, "db", database),
            patch.object(attendance_correction.frappe, "get_doc") as get_doc,
        ):
            attendance_correction.notify_current_reviewer_by_name("ACR-MISSING")

        get_doc.assert_not_called()

    def test_direct_hr_request_does_not_share_with_employee_approvers(self):
        doc = frappe._dict(
            name="ACR-TEST-00001",
            employee="HR-EMP-00062",
            approval_stage="Pending HR Approval",
        )
        with (
            patch.object(attendance_correction, "get_employee_approvers") as get_approvers,
            patch.object(attendance_correction, "_share_with_reviewer") as share,
            patch.object(attendance_correction, "_hr_managers", return_value=["hr@example.com"]),
            patch.object(attendance_correction, "_notify") as notify,
            patch.object(attendance_correction, "_", side_effect=lambda message: message),
        ):
            attendance_correction.notify_current_reviewer(doc)

        get_approvers.assert_not_called()
        share.assert_not_called()
        notify.assert_called_once()
        self.assertEqual(notify.call_args.args[0], "hr@example.com")

    def test_employee_without_desk_user_is_not_added_as_docshare_user(self):
        def exists(doctype, name):
            return doctype == "Employee" and name == "HR-EMP-APPROVER"

        database = SimpleNamespace(
            exists=exists,
            get_value=lambda *args, **kwargs: None,
        )
        with (
            patch.object(attendance_correction.frappe, "db", database),
            patch.object(attendance_correction, "add_docshare") as add_share,
        ):
            attendance_correction._share_with_reviewer(
                frappe._dict(doctype="Attendance Correction Request", name="ACR-TEST-00001"),
                "HR-EMP-APPROVER",
            )
        add_share.assert_not_called()


if __name__ == "__main__":
    unittest.main()
