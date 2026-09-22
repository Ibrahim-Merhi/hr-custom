import frappe
from frappe import _
from frappe.utils import formatdate


def ensure_push_relay_registration():
    """Register this site with the configured Frappe relay and return readiness."""
    from frappe.push_notification import PushNotification

    push = PushNotification("hrms")
    if not push.is_enabled():
        frappe.throw(_("Push Notification Relay is not enabled."))
    api_key, api_secret = push._get_credential()
    return {"enabled": True, "registered": bool(api_key and api_secret)}


def notify_salary_slip_available(doc, method=None):
    if not frappe.db.get_single_value("HR Mobile Attendance Settings", "notify_salary_slip_submission"):
        return
    user = frappe.db.get_value("Employee", doc.employee, "user_id")
    if not user or frappe.db.exists("PWA Notification", {"to_user": user, "reference_document_type": "Salary Slip", "reference_document_name": doc.name}):
        return
    notification = frappe.new_doc("PWA Notification")
    notification.from_user = frappe.session.user
    notification.to_user = user
    notification.message = _("Your salary slip for {0} to {1} is now available.").format(formatdate(doc.start_date), formatdate(doc.end_date))
    notification.reference_document_type = "Salary Slip"
    notification.reference_document_name = doc.name
    notification.insert(ignore_permissions=True)
