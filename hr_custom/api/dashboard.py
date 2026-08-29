import frappe
from frappe.utils import getdate, nowdate


@frappe.whitelist()
def get_summary(date=None, company=None, branch=None):
    if not {"HR User", "HR Manager", "System Manager"}.intersection(frappe.get_roles()):
        frappe.throw("Not permitted", frappe.PermissionError)
    date = getdate(date or nowdate())
    employee_filters = {"status": "Active"}
    if company: employee_filters["company"] = company
    if branch: employee_filters["branch"] = branch
    employees = frappe.get_all("Employee", filters=employee_filters, fields=["name", "branch"])
    names = [row.name for row in employees]
    if not names:
        return {"date": date, "total_employees": 0, "checked_in": 0, "not_checked_in": 0, "late": 0, "on_leave": 0, "absent": 0, "exceptions": 0, "branches": []}
    checkins = frappe.get_all("Employee Checkin", filters={"employee": ("in", names), "time": ("between", [f"{date} 00:00:00", f"{date} 23:59:59"])}, fields=["employee", "log_type", "custom_is_late"])
    checked = {row.employee for row in checkins if row.log_type == "IN"}
    late = {row.employee for row in checkins if row.custom_is_late}
    attendance = frappe.get_all("Attendance", filters={"employee": ("in", names), "attendance_date": date, "docstatus": ("<", 2)}, fields=["employee", "status"])
    on_leave = {row.employee for row in attendance if row.status == "On Leave"}
    absent = {row.employee for row in attendance if row.status == "Absent"}
    exceptions = frappe.db.count("Attendance Exception", {"employee": ("in", names), "attendance_date": date, "status": "Open"})
    branch_counts = {}
    for row in employees:
        branch_counts.setdefault(row.branch or "Not Set", {"branch": row.branch or "Not Set", "total": 0, "checked_in": 0})
        branch_counts[row.branch or "Not Set"]["total"] += 1
        branch_counts[row.branch or "Not Set"]["checked_in"] += int(row.name in checked)
    return {"date": date, "total_employees": len(names), "checked_in": len(checked), "not_checked_in": len(set(names)-checked-on_leave), "late": len(late), "on_leave": len(on_leave), "absent": len(absent), "exceptions": exceptions, "branches": list(branch_counts.values())}
