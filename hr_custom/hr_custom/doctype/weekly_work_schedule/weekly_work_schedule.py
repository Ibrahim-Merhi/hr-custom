import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from hr_custom.services.work_schedule import validate_schedule_document


class WeeklyWorkSchedule(Document):
    def validate(self):
        validate_schedule_document(self)


@frappe.whitelist()
def assign_employees(schedule, employees):
    if not frappe.has_permission("Weekly Work Schedule", "write", schedule):
        frappe.throw(_("You do not have permission to assign this schedule."), frappe.PermissionError)
    employees = frappe.parse_json(employees) if isinstance(employees, str) else employees
    assigned = 0
    for employee in set(employees or []):
        if not frappe.has_permission("Employee", "write", employee):
            frappe.throw(_("You do not have permission to update Employee {0}.").format(frappe.bold(employee)), frappe.PermissionError)
        frappe.db.set_value("Employee", employee, {
            "custom_weekly_work_schedule": schedule,
            "custom_use_custom_work_schedule": 0,
        }, update_modified=True)
        assigned += 1
    return {"assigned": cint(assigned)}
