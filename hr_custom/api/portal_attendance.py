import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from hr_custom.api.mobile_attendance import _employee_for_user, _validated_period


@frappe.whitelist()
def get_attendance_period(from_date=None, to_date=None):
    """Return official attendance plus unprocessed punches for the ESS user.

    This endpoint intentionally lives in its own module so production workers
    that cached an older mobile_attendance module can load the corrected
    history implementation immediately.
    """
    employee = _employee_for_user()
    start, end = _validated_period(from_date, to_date)
    rows = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee.name,
            "attendance_date": ["between", [start, end]],
            "docstatus": 1,
        },
        fields=[
            "name",
            "employee",
            "attendance_date",
            "status",
            "in_time",
            "out_time",
            "working_hours",
            "late_entry",
            "early_exit",
            "custom_check_in_branch",
            "custom_check_out_branch",
        ],
        order_by="attendance_date desc",
        limit=370,
    )
    correction_by_date = {
        getdate(row.attendance_date): row
        for row in frappe.get_all(
            "Attendance Correction Request",
            filters={"employee": employee.name, "attendance_date": ["between", [start, end]], "docstatus": ["<", 2]},
            fields=["name", "attendance_date", "status", "approval_stage"],
            order_by="creation desc",
        )
    }
    for row in rows:
        status = (row.status or "").lower()
        if status == "present":
            row.category = "present"
        elif status == "absent":
            row.category = "absent"
        elif status in ("on leave", "leave"):
            row.category = "leaves"
        else:
            row.category = "abnormal"
        correction = correction_by_date.get(getdate(row.attendance_date))
        row.correction_request = correction.name if correction else None
        row.correction_status = (correction.approval_stage or correction.status) if correction else None
    official_dates = {getdate(row.attendance_date) for row in rows}
    punches = frappe.get_all(
        "Employee Checkin",
        filters=[
            ["employee", "=", employee.name],
            ["time", ">=", start],
            ["time", "<", add_days(end, 1)],
            ["attendance", "is", "not set"],
        ],
        fields=["name", "time", "log_type"],
        order_by="time asc",
    )
    by_date = {}
    for punch in punches:
        punch_date = getdate(punch.time)
        if punch_date not in official_dates:
            by_date.setdefault(punch_date, []).append(punch)

    for attendance_date, logs in by_date.items():
        first_in = next((log.time for log in logs if log.log_type == "IN"), None)
        last_out = next((log.time for log in reversed(logs) if log.log_type == "OUT"), None)
        working_hours = (
            max(0, (last_out - first_in).total_seconds() / 3600)
            if first_in and last_out and last_out > first_in
            else 0
        )
        rows.append(
            frappe._dict(
                name=None,
                employee=employee.name,
                attendance_date=attendance_date,
                status=_("Pending"),
                in_time=first_in,
                out_time=last_out,
                working_hours=working_hours,
                late_entry=0,
                early_exit=0,
                is_pending=1,
                category="abnormal",
                correction_request=(correction_by_date.get(attendance_date) or {}).get("name"),
                correction_status=(correction_by_date.get(attendance_date) or {}).get("approval_stage") or (correction_by_date.get(attendance_date) or {}).get("status"),
            )
        )

    return sorted(rows, key=lambda row: getdate(row.attendance_date), reverse=True)


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
    from hr_custom.services.work_schedule import get_scheduled_period

    schedule = get_scheduled_period(employee.name, attendance_date)
    punch_shift = next((row.shift for row in punches if row.shift), None)
    if punch_shift:
        shift = frappe.db.get_value("Shift Type", punch_shift, ["start_time", "end_time"], as_dict=True)
        if shift:
            schedule["from_time"] = shift.start_time
            schedule["to_time"] = shift.end_time
            schedule["shift"] = punch_shift
    first_in = next((row.time for row in punches if row.log_type == "IN"), None)
    last_out = next((row.time for row in reversed(punches) if row.log_type == "OUT"), None)
    recorded_hours = max(0, (last_out - first_in).total_seconds() / 3600) if first_in and last_out and last_out > first_in else 0
    schedule["recorded_hours"] = flt(recorded_hours, 2)
    schedule["complete"] = bool(first_in and last_out and last_out > first_in)
    return {"attendance_date": attendance_date, "attendance": attendance[0] if attendance else None, "punches": punches, "corrections": corrections, "schedule": schedule}


@frappe.whitelist(methods=["POST"])
def submit_attendance_correction(attendance_date, request_type, reason, requested_check_in_time=None, requested_check_out_time=None):
    employee = _employee_for_user()
    attendance_date = getdate(attendance_date)
    if request_type not in ("Missing Check In", "Missing Check Out", "Wrong Check In", "Wrong Check Out", "Other"):
        frappe.throw(_("Invalid correction type."))
    if frappe.db.exists("Attendance Correction Request", {"employee": employee.name, "attendance_date": attendance_date, "docstatus": ["<", 2], "status": ["not in", ["Rejected", "Applied"]]}):
        frappe.throw(_("A correction request for this date is already awaiting action."))
    original = None
    if request_type in ("Wrong Check In", "Wrong Check Out"):
        original = frappe.db.get_value(
            "Employee Checkin",
            {"employee": employee.name, "time": ["between", [attendance_date, add_days(attendance_date, 1)]], "log_type": "IN" if request_type == "Wrong Check In" else "OUT"},
            "name",
            order_by="time asc" if request_type == "Wrong Check In" else "time desc",
        )
    doc = frappe.get_doc({
        "doctype": "Attendance Correction Request",
        "employee": employee.name,
        "attendance_date": attendance_date,
        "request_type": request_type,
        "original_checkin": original,
        "requested_check_in_time": requested_check_in_time,
        "requested_check_out_time": requested_check_out_time,
        "reason": (reason or "").strip(),
    })
    from hr_custom.services.attendance_correction import initialize_correction_approval
    initialize_correction_approval(doc)
    # Employee identity is derived from the authenticated session above; use
    # ignore_permissions only for the insert/submit mechanics so Website Users
    # do not need broad Desk access to the correction DocType.
    doc.insert(ignore_permissions=True)
    # Approval happens while the request is a draft. Final HR approval is the
    # only step that submits it, preventing employee submissions from locking
    # the approver fields and child approval rows.
    return {"name": doc.name, "status": doc.status, "approval_stage": doc.approval_stage}


@frappe.whitelist()
def get_correction_detail(name):
    from hr_custom.services.attendance_correction import get_correction_context
    from hr_custom.services.simple_leave import _is_hr_manager

    doc = frappe.get_doc("Attendance Correction Request", name)
    from hr_custom.services.portal_identity import get_effective_approval_user
    own_employee = _employee_for_user().name
    if doc.employee != own_employee and doc.current_approver != get_effective_approval_user() and not _is_hr_manager():
        frappe.throw(_("You are not permitted to view this correction request."), frappe.PermissionError)
    return {
        "name": doc.name, "employee": doc.employee, "employee_name": doc.employee_name,
        "attendance_date": doc.attendance_date, "request_type": doc.request_type,
        "requested_check_in_time": doc.requested_check_in_time, "requested_check_out_time": doc.requested_check_out_time,
        "reason": doc.reason, "status": doc.status, "stage": doc.approval_stage,
        "hr_override_note": doc.hr_override_note,
        "steps": [{"approver": row.approver, "approver_name": row.approver_name, "status": row.status, "remarks": row.remarks} for row in doc.approval_steps],
        "context": get_correction_context(doc),
    }


@frappe.whitelist()
def get_correction_approval_queue():
    from hr_custom.services.simple_leave import _is_hr_manager, get_current_approver_employee
    from hr_custom.services.portal_identity import get_effective_approval_user, has_portal_role

    user = get_effective_approval_user()
    approver_employee = get_current_approver_employee()
    is_hr = _is_hr_manager()
    fields = ["name", "employee", "employee_name", "attendance_date", "request_type", "reason", "approval_stage", "current_approver", "creation"]
    rows = frappe.get_all("Attendance Correction Request", filters={"docstatus": ["<", 2], "approval_stage": "Pending Approver Approval", "current_approver": user}, fields=fields, order_by="creation asc")
    for row in rows:
        row.review_mode = "approver"
    if is_hr:
        existing = {row.name for row in rows}
        for row in frappe.get_all("Attendance Correction Request", filters={"docstatus": ["<", 2], "approval_stage": ["in", ["Pending Approver Approval", "Pending HR Approval"]]}, fields=fields, order_by="creation asc"):
            if row.name not in existing:
                row.review_mode = "hr_override" if row.approval_stage == "Pending Approver Approval" else "hr"
                rows.append(row)
    configured = has_portal_role("Leave Approver") and frappe.db.exists("Employee Leave Approver", {"approver": approver_employee, "enabled": 1})
    return {"items": rows, "can_review": bool(is_hr or configured)}
