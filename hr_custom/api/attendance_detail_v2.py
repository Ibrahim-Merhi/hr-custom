import importlib

import frappe
from frappe.utils import add_days, flt, getdate

from hr_custom.api.mobile_attendance import _employee_for_user
work_schedule = importlib.reload(importlib.import_module("hr_custom.services.work_schedule"))


@frappe.whitelist()
def get_attendance_detail(attendance_date):
    employee = _employee_for_user()
    attendance_date = getdate(attendance_date)
    attendance = frappe.get_all(
        "Attendance",
        filters={"employee": employee.name, "attendance_date": attendance_date, "docstatus": 1},
        fields=["name", "attendance_date", "status", "in_time", "out_time", "working_hours", "late_entry", "early_exit", "shift"],
        limit=1,
    )
    punches = frappe.get_all(
        "Employee Checkin",
        filters=[
            ["employee", "=", employee.name],
            ["time", ">=", attendance_date],
            ["time", "<", add_days(attendance_date, 1)],
        ],
        fields=["name", "time", "log_type", "shift", "attendance", "custom_checkin_source", "custom_branch"],
        order_by="time asc",
    )
    corrections = frappe.get_all(
        "Attendance Correction Request",
        filters={"employee": employee.name, "attendance_date": attendance_date, "docstatus": ["<", 2]},
        fields=["name", "request_type", "status", "approval_stage", "reason", "requested_check_in_time", "requested_check_out_time", "creation"],
        order_by="creation desc",
    )
    schedule = work_schedule.get_scheduled_period(employee.name, attendance_date)
    punch_shift = next((row.shift for row in punches if row.shift), None)
    if punch_shift:
        shift = frappe.db.get_value("Shift Type", punch_shift, ["start_time", "end_time"], as_dict=True)
        if shift:
            schedule["from_time"] = shift.start_time
            schedule["to_time"] = shift.end_time
            schedule["shift"] = punch_shift
    first_in = next((row.time for row in punches if row.log_type == "IN"), None)
    last_out = next((row.time for row in reversed(punches) if row.log_type == "OUT"), None)
    schedule["recorded_hours"] = flt((last_out - first_in).total_seconds() / 3600, 2) if first_in and last_out and last_out > first_in else 0
    schedule["complete"] = bool(first_in and last_out and last_out > first_in)
    return {
        "attendance_date": attendance_date,
        "attendance": attendance[0] if attendance else None,
        "punches": punches,
        "corrections": corrections,
        "schedule": schedule,
    }
