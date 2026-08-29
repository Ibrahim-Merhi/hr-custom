import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
class AttendanceCorrectionRequest(Document):
    def validate(self):
        if "HR Manager" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
            own = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")
            if not own or self.employee != own: frappe.throw(_("You may only request a correction for yourself."), frappe.PermissionError)
    def on_update_after_submit(self):
        if self.status == "Approved" and not self.approved_by:
            self.db_set("approved_by", frappe.session.user); self.db_set("approval_date", now_datetime())
