import frappe
from frappe import _

from hr_custom.services.hourly_leave import calculate_hourly_leave, get_hour_leave_balance
from hr_custom.services.work_schedule import get_leave_unit

HR_ROLES = {"HR User", "HR Manager", "System Manager"}


def _check_employee_access(employee: str):
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in."), frappe.PermissionError)
    if HR_ROLES.intersection(frappe.get_roles()):
        return
    from hr_custom.services.portal_identity import get_portal_employee
    own_employee = get_portal_employee(fields=["name"]).name
    if employee != own_employee:
        frappe.throw(_("You are not permitted to view this employee's leave information."), frappe.PermissionError)


@frappe.whitelist()
def get_hourly_leave_preview(employee, leave_type, from_date, to_date, leave_duration=None, partial_hours=None):
    _check_employee_access(employee)
    result = calculate_hourly_leave(
        employee, leave_type, from_date, to_date, leave_duration, partial_hours
    )
    balance = get_hour_leave_balance(employee, leave_type, from_date)
    result["balance"] = balance
    result["balance_after_leave"] = balance["remaining_hours"] - result["total_leave_hours"]
    return result


@frappe.whitelist()
def get_leave_unit_for_type(leave_type):
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in."), frappe.PermissionError)
    return get_leave_unit(leave_type)
