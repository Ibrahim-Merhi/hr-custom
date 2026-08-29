import hashlib
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class EmployeeAttendanceDevice(Document):
    def validate(self):
        if self.user_agent and not self.user_agent_hash:
            self.user_agent_hash = hashlib.sha256(self.user_agent.encode()).hexdigest()
        duplicate = frappe.db.exists("Employee Attendance Device", {"employee": self.employee, "device_id": self.device_id, "name": ("!=", self.name)})
        if duplicate:
            frappe.throw(_("This device is already registered for the employee."))
        if self.is_new() and not self.registered_on:
            self.registered_on = now_datetime()

