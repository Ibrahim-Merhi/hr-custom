import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hr_custom.services.portal_notifications import notify_salary_slip_available


class TestPortalNotifications(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.user = "portal.notification.test@example.com"
        self.employee = make_employee(self.user, company="_Test Company")
        frappe.db.set_single_value("HR Mobile Attendance Settings", "notify_salary_slip_submission", 1)

    def tearDown(self):
        frappe.db.rollback()

    def test_salary_slip_notification_is_created_once(self):
        slip = frappe._dict(name="SAL-NOTIFY-TEST", employee=self.employee, start_date="2027-01-01", end_date="2027-01-31")
        notify_salary_slip_available(slip)
        notify_salary_slip_available(slip)
        filters = {"to_user": self.user, "reference_document_type": "Salary Slip", "reference_document_name": slip.name}
        self.assertEqual(frappe.db.count("PWA Notification", filters), 1)
