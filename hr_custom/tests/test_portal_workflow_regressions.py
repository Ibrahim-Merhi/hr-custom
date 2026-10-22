import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from hr_custom.api import mobile_attendance, portal_admin, portal_auth
from hr_custom.services import attendance_correction, portal_identity, simple_leave, work_schedule, workspace_cards


class TestPortalImpersonationSecurity(unittest.TestCase):
    def test_portal_cookie_is_persistent_for_installed_pwa(self):
        request = SimpleNamespace(scheme="https", headers={})
        cookie_manager = SimpleNamespace(set_cookie=lambda *args, **kwargs: None)
        local = frappe._dict(request=request, cookie_manager=cookie_manager)
        with (
            patch.object(portal_identity.frappe, "local", local),
            patch.object(cookie_manager, "set_cookie", wraps=cookie_manager.set_cookie) as set_cookie,
        ):
            portal_identity.set_portal_cookie("portal-token")

        args, kwargs = set_cookie.call_args
        self.assertEqual(args, (portal_identity.PORTAL_COOKIE, "portal-token"))
        self.assertEqual(kwargs["max_age"], portal_identity.PORTAL_COOKIE_MAX_AGE)
        self.assertIsNotNone(kwargs["expires"])
        self.assertTrue(kwargs["httponly"])
        self.assertTrue(kwargs["secure"])

    def test_only_administrator_can_start_impersonation(self):
        with (
            patch.object(portal_auth.frappe, "session", frappe._dict(user="hr.manager@example.com")),
            patch.object(portal_auth, "has_portal_role", return_value=False),
            patch.object(portal_auth.frappe, "throw", side_effect=frappe.PermissionError),
        ):
            with self.assertRaises(frappe.PermissionError):
                portal_auth._require_administrator()

    def test_administrator_can_pass_impersonation_guard(self):
        with (
            patch.object(portal_auth.frappe, "session", frappe._dict(user="Administrator")),
            patch.object(portal_auth.frappe, "throw") as throw,
        ):
            portal_auth._require_administrator()

        throw.assert_not_called()

    def test_expired_impersonation_session_is_revoked(self):
        expired = frappe._dict(
            name="PORTAL-SESSION-EXPIRED",
            credential="HR-EMP-00062",
            last_seen=None,
            is_impersonation=1,
            impersonated_by="Administrator",
            impersonation_reason="Troubleshooting",
            expires_on=datetime(2026, 10, 10, 11, 59),
        )
        database = SimpleNamespace(
            get_value=lambda *args, **kwargs: expired,
            set_value=lambda *args, **kwargs: None,
        )
        local = frappe._dict(
            request=SimpleNamespace(cookies={portal_identity.PORTAL_COOKIE: "raw-token"}),
        )
        with (
            patch.object(portal_identity.frappe, "db", database),
            patch.object(portal_identity.frappe, "local", local),
            patch.object(portal_identity, "now_datetime", return_value=datetime(2026, 10, 10, 12, 0)),
            patch.object(database, "set_value", wraps=database.set_value) as set_value,
        ):
            self.assertIsNone(portal_identity.get_portal_session(renew=False))

        set_value.assert_called_once_with(
            "Employee Portal Session",
            "PORTAL-SESSION-EXPIRED",
            "revoked",
            1,
            update_modified=False,
        )

    def test_portal_administrator_inherits_all_portal_roles(self):
        credential = frappe._dict(roles=[frappe._dict(portal_role="Portal Administrator")])
        with patch.object(portal_identity, "get_portal_credential", return_value=credential):
            self.assertEqual(
                portal_identity.get_portal_roles(),
                {"Portal Administrator", "Employee", "Leave Approver", "HR"},
            )

    def test_portal_administrator_never_inherits_stale_employee_identity(self):
        credential = frappe._dict(account_type="Portal Administrator", employee="E000")
        with patch.object(simple_leave, "get_portal_credential", return_value=credential):
            self.assertIsNone(simple_leave.get_current_approver_employee())

    def test_non_admin_portal_user_cannot_change_settings(self):
        with (
            patch.object(mobile_attendance, "has_portal_role", return_value=False),
            patch.object(mobile_attendance.frappe, "throw", side_effect=frappe.PermissionError),
        ):
            with self.assertRaises(frappe.PermissionError):
                mobile_attendance._require_portal_administrator()

    def test_non_admin_portal_user_cannot_access_admin_data(self):
        with (
            patch.object(portal_admin, "has_portal_role", return_value=False),
            patch.object(portal_admin.frappe, "throw", side_effect=frappe.PermissionError),
        ):
            with self.assertRaises(frappe.PermissionError):
                portal_admin._require_admin()


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


class TestMobileClockState(unittest.TestCase):
    def test_latest_checkin_controls_the_next_action(self):
        latest = frappe._dict(log_type="IN", time=datetime(2026, 10, 22, 8, 0))
        with (
            patch.object(mobile_attendance, "_latest", return_value=latest),
            patch.object(mobile_attendance.frappe.db, "get_value") as get_value,
        ):
            action, source = mobile_attendance._clock_action("HR-EMP-00001", date(2026, 10, 22))

        self.assertEqual(action, "OUT")
        self.assertIs(source, latest)
        get_value.assert_not_called()

    def test_hr_entered_open_attendance_allows_employee_to_clock_out(self):
        attendance = frappe._dict(
            name="HR-ATT-2026-00001",
            in_time=datetime(2026, 10, 22, 8, 0),
            out_time=None,
        )
        with (
            patch.object(mobile_attendance, "_latest", return_value=None),
            patch.object(mobile_attendance.frappe.db, "get_value", return_value=attendance),
        ):
            action, source = mobile_attendance._clock_action("HR-EMP-00001", date(2026, 10, 22))

        self.assertEqual(action, "OUT")
        self.assertEqual(source.name, attendance.name)
        self.assertEqual(source.source, "HR Attendance")

    def test_completed_hr_attendance_does_not_open_an_extra_clock_out(self):
        attendance = frappe._dict(
            name="HR-ATT-2026-00001",
            in_time=datetime(2026, 10, 22, 8, 0),
            out_time=datetime(2026, 10, 22, 16, 0),
        )
        with (
            patch.object(mobile_attendance, "_latest", return_value=None),
            patch.object(mobile_attendance.frappe.db, "get_value", return_value=attendance),
        ):
            action, source = mobile_attendance._clock_action("HR-EMP-00001", date(2026, 10, 22))

        self.assertEqual(action, "IN")
        self.assertIsNone(source)


class TestHRWorkspaceCards(unittest.TestCase):
    def test_active_employee_card_is_not_limited_to_one_company(self):
        database = SimpleNamespace(count=lambda *args, **kwargs: 172)
        with (
            patch.object(workspace_cards.frappe, "db", database),
            patch.object(database, "count", wraps=database.count) as count,
        ):
            result = workspace_cards.active_employees()

        filters = count.call_args.args[1]
        self.assertNotIn("company", filters)
        self.assertEqual(filters["status"], "Active")
        self.assertEqual(filters["custom_is_payroll_identity"], 0)
        self.assertNotIn("company", result["route_options"])

    def test_absent_card_uses_schedule_aware_status(self):
        statuses = {"EARLY": "Scheduled", "ABSENT": "Absent", "OFF": "Non-working"}
        with (
            patch.object(workspace_cards, "_active_employee_names", return_value=list(statuses)),
            patch.object(workspace_cards, "_present_employee_names", return_value={"PRESENT"}),
            patch.object(
                workspace_cards,
                "get_unpunched_attendance_status",
                side_effect=lambda employee, *_: statuses[employee],
            ),
        ):
            result = workspace_cards.absent_today()

        self.assertEqual(result["value"], 1)


class TestScheduleAwareAbsence(unittest.TestCase):
    def _status(self, hours, start, current, holiday=False):
        with (
            patch.object(
                work_schedule,
                "get_scheduled_period",
                return_value={"working_hours": hours, "from_time": start},
            ),
            patch.object(work_schedule, "get_holiday_status", return_value=holiday),
        ):
            return work_schedule.get_unpunched_attendance_status(
                "HR-EMP-00001", date(2026, 10, 22), current
            )

    def test_employee_is_not_absent_before_scheduled_start(self):
        self.assertEqual(
            self._status(8, "12:00:00", datetime(2026, 10, 22, 10, 0)),
            "Scheduled",
        )

    def test_employee_is_absent_after_scheduled_start(self):
        self.assertEqual(
            self._status(8, "12:00:00", datetime(2026, 10, 22, 12, 1)),
            "Absent",
        )

    def test_zero_hour_day_is_not_absent(self):
        self.assertEqual(
            self._status(0, None, datetime(2026, 10, 22, 18, 0)),
            "Non-working",
        )

    def test_holiday_is_not_absent(self):
        self.assertEqual(
            self._status(8, "08:00:00", datetime(2026, 10, 22, 18, 0), holiday=True),
            "Non-working",
        )


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
