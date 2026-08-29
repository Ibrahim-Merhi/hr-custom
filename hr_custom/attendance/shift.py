from datetime import timedelta

import frappe
from frappe.utils import cint
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift


def resolve_shift(employee, timestamp):
    details = get_employee_shift(employee, timestamp, consider_default_shift=True)
    if not details:
        return None
    shift = details.shift_type
    return frappe._dict(
        name=shift.name,
        start=details.start_datetime,
        end=details.end_datetime,
        actual_start=details.actual_start,
        actual_end=details.actual_end,
        late_grace=cint(shift.late_entry_grace_period),
        early_grace=cint(shift.early_exit_grace_period),
        enable_late=cint(shift.enable_late_entry_marking),
        enable_early=cint(shift.enable_early_exit_marking),
    )


def timing_flags(shift, timestamp, action):
    result = dict(is_late=0, minutes_late=0, is_early_exit=0, minutes_early=0)
    if not shift:
        return result
    if action == "IN" and timestamp > shift.start:
        result["minutes_late"] = max(0, int((timestamp - shift.start).total_seconds() // 60))
        result["is_late"] = int(shift.enable_late and timestamp > shift.start + timedelta(minutes=shift.late_grace))
    if action == "OUT" and timestamp < shift.end:
        result["minutes_early"] = max(0, int((shift.end - timestamp).total_seconds() // 60))
        result["is_early_exit"] = int(shift.enable_early and timestamp < shift.end - timedelta(minutes=shift.early_grace))
    return result

