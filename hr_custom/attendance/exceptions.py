import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate


@frappe.whitelist()
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
    if rows and rows[0].log_type == "OUT":
        _ensure(employee, date, rows[0].custom_branch, shift, "Missing Check In", f"First log {rows[0].name} is an OUT without a preceding IN.", last_checkout=rows[0].name)
    expected = "IN"
    for row in rows:
        if row.log_type != expected:
            _ensure(employee, date, row.custom_branch, shift, f"Duplicate {row.log_type}", f"Unexpected {row.log_type} log {row.name}.")
        expected = "OUT" if row.log_type == "IN" else "IN"
    if rows and rows[-1].log_type == "IN" and date < getdate(nowdate()):
        _ensure(employee, date, rows[-1].custom_branch, shift, "Missing Check Out", f"Last checkin {rows[-1].name} has no matching OUT.", first_checkin=rows[0].name)


def _ensure(employee, date, branch, shift, exception_type, details, first_checkin=None, last_checkout=None):
    key = {"employee": employee, "attendance_date": date, "exception_type": exception_type, "status": "Open"}
    if frappe.db.exists("Attendance Exception", key):
        return
    exception = frappe.get_doc({"doctype": "Attendance Exception", **key, "branch": branch, "shift_type": shift, "details": details, "first_checkin": first_checkin, "last_checkout": last_checkout}).insert(ignore_permissions=True)
    user = frappe.db.get_value("Employee", employee, "user_id")
    if user and exception_type == "Missing Check Out":
        frappe.get_doc({
            "doctype": "PWA Notification",
            "from_user": "Administrator",
            "to_user": user,
            "message": _("No clock-out was recorded for {0}. The day remains abnormal; please submit an attendance correction.").format(date),
            "reference_document_type": "Attendance Exception",
            "reference_document_name": exception.name,
        }).insert(ignore_permissions=True)

def process_one_shift_attendance(shift_type):
    """Administrative helper for processing one explicitly named shift."""
    frappe.get_doc("Shift Type", shift_type).process_auto_attendance()
