from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee


class TestHRAnnouncement(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = "_Test Company"
        cls.department = "Announcement Department - _TC"
        cls.employment_type = "Announcement Full Time"
        cls.target_email = "announcement.target@example.com"
        cls.other_email = "announcement.other@example.com"

    def setUp(self):
        frappe.set_user("Administrator")
        if not frappe.db.exists("Department", "Announcement Department - _TC"):
            frappe.get_doc({"doctype": "Department", "department_name": "Announcement Department", "company": self.company}).insert(ignore_permissions=True)
        if not frappe.db.exists("Employment Type", "Announcement Full Time"):
            frappe.get_doc({"doctype": "Employment Type", "employee_type_name": "Announcement Full Time"}).insert(ignore_permissions=True)
        self.target = make_employee(self.target_email, company=self.company)
        self.other = make_employee(self.other_email, company=self.company)
        frappe.db.set_value("Employee", self.target, {"department": self.department, "employment_type": self.employment_type, "status": "Active"})
        frappe.db.set_value("Employee", self.other, {"department": None, "employment_type": self.employment_type, "status": "Active"})

    def tearDown(self):
        frappe.db.rollback()

    def make_announcement(self):
        doc = frappe.get_doc({"doctype": "HR Announcement", "title": "Office update", "message": "Please review the new policy."})
        doc.append("departments", {"department": self.department})
        doc.append("employment_types", {"employment_type": self.employment_type})
        return doc

    def test_filters_are_combined_as_intersection(self):
        names = [row.name for row in self.make_announcement().get_target_employees()]
        self.assertIn(self.target, names)
        self.assertNotIn(self.other, names)

    ("hr_custom.overrides.pwa_notification.CustomPWANotification.send_push_notification")
    def test_portal_credential_is_valid_announcement_recipient(self, _push):
        portal_employee = make_employee("announcement.portal@example.com", company=self.company)
        frappe.db.set_value(
            "Employee",
            portal_employee,
            {"department": self.department, "employment_type": self.employment_type, "status": "Active", "user_id": None},
        )
        frappe.get_doc(
            {
                "doctype": "Employee Portal Credential",
                "employee": portal_employee,
                "username": f"announcement-{portal_employee}",
                "password": "Portal-Test-Password-123!",
                "enabled": 1,
                "roles": [{"portal_role": "Employee"}],
            }
        ).insert(ignore_permissions=True)

        recipients = {row.name: row.notification_user for row in self.make_announcement().get_target_employees()}
        self.assertEqual(recipients[portal_employee], f"portal::{portal_employee}")

        announcement = self.make_announcement().insert()
        announcement.submit()
        self.assertTrue(
            frappe.db.exists(
                "PWA Notification",
                {
                    "to_user": f"portal::{portal_employee}",
                    "reference_document_type": "HR Announcement",
                    "reference_document_name": announcement.name,
                },
            )
        )

    @patch("hr_custom.overrides.pwa_notification.CustomPWANotification.send_push_notification")
    def test_submit_creates_one_notification_per_target(self, _push):
        doc = self.make_announcement().insert()
        doc.submit()
        notifications = frappe.get_all("PWA Notification", filters={"reference_document_type": "HR Announcement", "reference_document_name": doc.name}, fields=["to_user", "message"])
        self.assertEqual([row.to_user for row in notifications], ["announcement.target@example.com"])
        self.assertEqual(notifications[0].message, "Office update\nPlease review the new policy.")
        self.assertEqual(frappe.db.get_value("HR Announcement", doc.name, "recipient_count"), 1)

    def test_target_is_required(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({"doctype": "HR Announcement", "title": "No target", "message": "Message"}).insert()
