import itertools

import frappe
from erpnext.setup.doctype.employee.employee import is_holiday
from frappe.utils import getdate
from hrms.hr.doctype.employee_checkin.employee_checkin import (
    calculate_working_hours,
    mark_attendance_and_link_log,
)


def process_pending_attendance():
    settings = frappe.get_single("HR Mobile Attendance Settings")
    if not settings.enable_attendance_processor:
        return
    if settings.auto_create_attendance:
        from hrms.hr.doctype.shift_type.shift_type import process_auto_attendance_for_all_shifts
        process_auto_attendance_for_all_shifts()
        if settings.allow_without_shift:
            process_unassigned_mobile_checkins()
    from hr_custom.attendance.exceptions import scan_recent_checkins
    scan_recent_checkins()


def finalize_previous_day():
    process_pending_attendance()


def process_unassigned_mobile_checkins(from_date=None, employee=None):
    """Create standard Attendance from completed no-shift mobile IN/OUT logs.

    This is a compatibility fallback only. Shift-linked logs remain exclusively owned
    by HRMS Auto Attendance, including overnight grouping and shift thresholds.
    """
    filters = {
        "custom_checkin_source": "Mobile GPS",
        "shift": ("is", "not set"),
        "attendance": ("is", "not set"),
        "skip_auto_attendance": 0,
    }
    if from_date:
        filters["time"] = (">=", getdate(from_date))
    if employee:
        filters["employee"] = employee
    logs = frappe.get_all(
        "Employee Checkin",
        filters=filters,
        fields=["name", "employee", "employee_name", "time", "log_type", "custom_branch"],
        order_by="employee,time",
    )
    for (_employee, attendance_date), rows in itertools.groupby(logs, key=lambda row: (row.employee, row.time.date())):
        _process_no_shift_day(_employee, attendance_date, list(rows))


def _process_no_shift_day(employee, attendance_date, logs):
    if not logs or logs[-1].log_type != "OUT":
        _ensure_exception(employee, attendance_date, logs, "Missing Check Out", "The final mobile event is IN; Attendance was not finalized.")
        return
    if logs[0].log_type != "IN":
        _ensure_exception(employee, attendance_date, logs, "Missing Check In", "The first mobile event is OUT; Attendance was not finalized.")
        return
    if frappe.db.exists("Attendance", {"employee": employee, "attendance_date": attendance_date, "docstatus": ("<", 2)}):
        _ensure_exception(employee, attendance_date, logs, "Attendance Conflict", "Attendance already exists; mobile logs were not allowed to overwrite it.")
        return
    if frappe.db.exists("Leave Application", {"employee": employee, "docstatus": 1, "from_date": ("<=", attendance_date), "to_date": (">=", attendance_date)}):
        _ensure_exception(employee, attendance_date, logs, "Leave Conflict", "Approved leave exists; mobile logs were not converted to Attendance.")
        return
    if is_holiday(employee, attendance_date, raise_exception=False):
        return
    working_hours, in_time, out_time = calculate_working_hours(
        logs,
        "Strictly based on Log Type in Employee Checkin",
        "Every Valid Check-in and Check-out",
    )
    if not in_time or not out_time or working_hours < 0:
        _ensure_exception(employee, attendance_date, logs, "Other", "No complete positive IN/OUT pair was found.")
        return
    mark_attendance_and_link_log(
        logs,
        "Present",
        attendance_date,
        working_hours,
        in_time=in_time,
        out_time=out_time,
        shift=None,
    )


def _ensure_exception(employee, attendance_date, logs, exception_type, details):
    key = {"employee": employee, "attendance_date": attendance_date, "exception_type": exception_type, "status": "Open"}
    if frappe.db.exists("Attendance Exception", key):
        return
    frappe.get_doc({
        "doctype": "Attendance Exception",
        **key,
        "branch": logs[0].custom_branch if logs else None,
        "details": details,
        "first_checkin": logs[0].name if logs else None,
        "last_checkout": logs[-1].name if logs and logs[-1].log_type == "OUT" else None,
    }).insert(ignore_permissions=True)
