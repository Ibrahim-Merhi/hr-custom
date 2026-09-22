import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    conditions = ["a.docstatus = 1", "a.attendance_date between %(from_date)s and %(to_date)s"]
    values = {"from_date": filters.from_date, "to_date": filters.to_date}
    if filters.employee:
        conditions.append("a.employee = %(employee)s")
        values["employee"] = filters.employee
    if filters.status:
        conditions.append("a.status = %(status)s")
        values["status"] = filters.status
    if filters.branch:
        conditions.append("(a.custom_check_in_branch = %(branch)s or a.custom_check_out_branch = %(branch)s)")
        values["branch"] = filters.branch
    data = frappe.db.sql(
        f"""select a.name, a.attendance_date, a.employee, a.employee_name, a.status,
            a.in_time, a.custom_check_in_branch, a.out_time, a.custom_check_out_branch,
            a.working_hours, a.shift, a.late_entry, a.early_exit
        from `tabAttendance` a where {' and '.join(conditions)}
        order by a.attendance_date desc, a.employee_name asc""",
        values,
        as_dict=True,
    )
    specs = [
        ("name", "Attendance", "Link", "Attendance", 150), ("attendance_date", "Date", "Date", None, 100),
        ("employee", "Employee", "Link", "Employee", 130), ("employee_name", "Employee Name", "Data", None, 180),
        ("status", "Status", "Data", None, 100), ("in_time", "Check In", "Datetime", None, 150),
        ("custom_check_in_branch", "Check-in Branch", "Link", "Branch", 130), ("out_time", "Check Out", "Datetime", None, 150),
        ("custom_check_out_branch", "Check-out Branch", "Link", "Branch", 130), ("working_hours", "Working Hours", "Float", None, 110),
        ("shift", "Shift", "Link", "Shift Type", 120), ("late_entry", "Late Entry", "Check", None, 80),
        ("early_exit", "Early Exit", "Check", None, 80),
    ]
    columns = [{"fieldname": field, "label": _(label), "fieldtype": fieldtype, "options": options, "width": width} for field, label, fieldtype, options, width in specs]
    return columns, data
