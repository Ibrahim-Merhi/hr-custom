import frappe
from frappe.utils import add_days, getdate, nowdate


def scan_recent_checkins(days=2):
    """Create one open exception per employee/date/type; safe to run repeatedly."""
    start = getdate(add_days(nowdate(), -int(days)))
    logs = frappe.get_all("Employee Checkin", filters={"time": (">=", start)}, fields=["name", "employee", "time", "log_type", "shift", "custom_branch"], order_by="employee,time")
    groups = {}
    for log in logs:
        groups.setdefault((log.employee, log.time.date(), log.shift), []).append(log)
    for (employee, date, shift), rows in groups.items():
        _scan_group(employee, date, shift, rows)


def _scan_group(employee, date, shift, rows):
    expected = "IN"
    for row in rows:
        if row.log_type != expected:
            _ensure(employee, date, row.custom_branch, shift, f"Duplicate {row.log_type}", f"Unexpected {row.log_type} log {row.name}.")
        expected = "OUT" if row.log_type == "IN" else "IN"
    if rows and rows[-1].log_type == "IN" and date < getdate(nowdate()):
        _ensure(employee, date, rows[-1].custom_branch, shift, "Missing Check Out", f"Last checkin {rows[-1].name} has no matching OUT.", first_checkin=rows[0].name)


def _ensure(employee, date, branch, shift, exception_type, details, first_checkin=None):
    key = {"employee": employee, "attendance_date": date, "exception_type": exception_type, "status": "Open"}
    if frappe.db.exists("Attendance Exception", key):
        return
    frappe.get_doc({"doctype": "Attendance Exception", **key, "branch": branch, "shift_type": shift, "details": details, "first_checkin": first_checkin}).insert(ignore_permissions=True)

