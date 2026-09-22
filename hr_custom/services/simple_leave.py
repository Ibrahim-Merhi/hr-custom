from __future__ import annotations

import frappe
from frappe import _
from frappe.share import add_docshare
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

from hr_custom.services.work_schedule import get_employee_schedule, get_holidays, get_leave_unit


def validate_employee_leave_setup(doc, method=None):
    if doc.doctype != "Employee":
        return
    seen = set()
    enabled = []
    for index, row in enumerate(doc.get("custom_leave_approvers") or [], 1):
        if row.approver in seen:
            frappe.throw(_("Leave approver {0} appears more than once.").format(frappe.bold(row.approver)))
        seen.add(row.approver)
        if row.enabled:
            row.sequence = row.sequence or index
            enabled.append(row)
    enabled.sort(key=lambda row: (row.sequence, row.idx or 0))
    if enabled:
        doc.leave_approver = enabled[0].approver


def get_employee_approvers(employee):
    rows = frappe.get_all("Employee Leave Approver", filters={"parent": employee, "parenttype": "Employee", "parentfield": "custom_leave_approvers", "enabled": 1}, fields=["approver", "sequence", "idx"], order_by="sequence asc, idx asc")
    if rows:
        return [row.approver for row in rows]
    standard = frappe.db.get_value("Employee", employee, "leave_approver")
    return [standard] if standard else []


def initialize_leave_approval(doc, method=None):
    """Build an immutable, ordered approval route from the Employee setup."""
    if doc.doctype != "Leave Application" or doc.get("custom_approval_steps"):
        return
    approvers = get_employee_approvers(doc.employee)
    if not approvers:
        return
    for sequence, approver in enumerate(approvers, 1):
        doc.append("custom_approval_steps", {
            "approver": approver,
            "sequence": sequence,
            "status": "Pending",
        })
    doc.custom_approval_stage = "Pending Approver Approval"
    doc.custom_current_approver = approvers[0]
    doc.leave_approver = approvers[0]
    doc.status = "Open"


def _notify_reviewer(user, doc, event, text):
    if not user:
        return
    notification = frappe.new_doc("PWA Notification")
    notification.from_user = frappe.session.user
    notification.to_user = user
    notification.message = text
    notification.reference_document_type = "Leave Application"
    notification.reference_document_name = doc.name
    notification.insert(ignore_permissions=True)


def _share_with_reviewer(doc, user):
    """Grant workflow access without requiring the employee to share records."""
    add_docshare(
        doc.doctype,
        doc.name,
        user=user,
        read=1,
        write=1,
        share=0,
        notify=0,
        flags={"ignore_share_permission": True},
    )


def _hr_managers():
    return frappe.get_all(
        "Has Role",
        filters={"role": ["in", ["HR Manager", "System Manager"]], "parenttype": "User"},
        pluck="parent",
        distinct=True,
    )


def notify_leave_workflow(doc, method=None):
    """Share the request and notify only the reviewer whose turn it is."""
    approvers = get_employee_approvers(doc.employee)
    for approver in approvers:
        _share_with_reviewer(doc, approver)
    if doc.custom_current_approver:
        _notify_reviewer(
            doc.custom_current_approver,
            doc,
            "approver-1",
            _("Leave request {0} is waiting for your approval.").format(doc.name),
        )


def _notify_next_reviewer(doc):
    if doc.custom_approval_stage == "Pending Approver Approval" and doc.custom_current_approver:
        pending = next((row for row in doc.custom_approval_steps if row.status == "Pending" and row.approver == doc.custom_current_approver), None)
        event = f"approver-{pending.sequence if pending else 0}"
        _notify_reviewer(doc.custom_current_approver, doc, event, _("Leave request {0} is waiting for your approval.").format(doc.name))
    elif doc.custom_approval_stage == "Pending HR Approval":
        for user in _hr_managers():
            _notify_reviewer(user, doc, "hr", _("Leave request {0} completed employee approvals and is waiting for final HR approval.").format(doc.name))


def _is_hr_manager(user=None):
    return bool({"HR Manager", "System Manager"}.intersection(frappe.get_roles(user or frappe.session.user)))


@frappe.whitelist()
def get_leave_approval_context(name):
    doc = frappe.get_doc("Leave Application", name)
    # Bring existing portal requests created before this workflow was installed
    # into the approval route when they are first opened.
    if doc.docstatus == 0 and doc.status == "Open" and not doc.custom_approval_stage:
        initialize_leave_approval(doc)
        if doc.custom_approval_stage:
            doc.flags.ignore_permissions = True
            doc.save()
            notify_leave_workflow(doc)
    user = frappe.session.user
    can_act = (
        doc.docstatus == 0
        and (
            (doc.custom_approval_stage == "Pending Approver Approval" and doc.custom_current_approver == user)
            or (doc.custom_approval_stage == "Pending HR Approval" and _is_hr_manager(user))
        )
    )
    return {
        "stage": doc.custom_approval_stage,
        "current_approver": doc.custom_current_approver,
        "can_act": can_act,
        "is_final_hr_step": doc.custom_approval_stage == "Pending HR Approval",
    }


@frappe.whitelist(methods=["POST"])
def process_leave_approval(name, action, remarks=None):
    if action not in ("approve", "reject"):
        frappe.throw(_("Invalid approval action."))
    # Serialize reviewers so two devices cannot advance the same step twice.
    frappe.db.sql("select name from `tabLeave Application` where name=%s for update", name)
    doc = frappe.get_doc("Leave Application", name)
    if doc.docstatus == 0 and doc.status == "Open" and not doc.custom_approval_stage:
        initialize_leave_approval(doc)
        if doc.custom_approval_stage:
            doc.flags.ignore_permissions = True
            doc.save()
    if doc.docstatus != 0 or doc.custom_approval_stage not in ("Pending Approver Approval", "Pending HR Approval"):
        frappe.throw(_("This leave request is no longer waiting for approval."))

    user = frappe.session.user
    is_hr_step = doc.custom_approval_stage == "Pending HR Approval"
    if is_hr_step:
        if not _is_hr_manager(user):
            frappe.throw(_("Only an HR Manager can complete the final approval."), frappe.PermissionError)
    elif doc.custom_current_approver != user:
        frappe.throw(_("This leave request is waiting for another approver."), frappe.PermissionError)

    current_step = next((row for row in doc.custom_approval_steps if row.status == "Pending" and row.approver == user), None)
    if current_step:
        current_step.status = "Approved" if action == "approve" else "Rejected"
        current_step.acted_on = now_datetime()
        current_step.remarks = (remarks or "").strip()

    if action == "reject":
        doc.custom_approval_stage = "Rejected"
        doc.custom_current_approver = None
        doc.status = "Rejected"
        doc.flags.ignore_permissions = True
        doc.save()
        doc.submit()
        return {"name": doc.name, "stage": doc.custom_approval_stage, "status": doc.status, "docstatus": doc.docstatus}

    if not is_hr_step:
        next_step = next((row for row in sorted(doc.custom_approval_steps, key=lambda row: (row.sequence, row.idx)) if row.status == "Pending"), None)
        if next_step:
            doc.custom_current_approver = next_step.approver
        else:
            doc.custom_approval_stage = "Pending HR Approval"
            doc.custom_current_approver = None
        doc.flags.ignore_permissions = True
        doc.save()
        _notify_next_reviewer(doc)
        return {"name": doc.name, "stage": doc.custom_approval_stage, "status": doc.status, "docstatus": doc.docstatus}

    doc.custom_approval_stage = "Approved"
    doc.custom_current_approver = None
    doc.status = "Approved"
    doc.flags.ignore_permissions = True
    doc.save()
    doc.submit()
    return {"name": doc.name, "stage": doc.custom_approval_stage, "status": doc.status, "docstatus": doc.docstatus}


def select_leave_type(employee, from_date, to_date, leave_unit=None, requested_leave_type=None):
    employee_values = frappe.db.get_value("Employee", employee, ["custom_default_mobile_leave_type"], as_dict=True)
    allocations = frappe.get_all("Leave Allocation", filters={"employee": employee, "docstatus": 1, "from_date": ["<=", from_date], "to_date": [">=", to_date]}, fields=["leave_type"], distinct=True)
    candidates = [row.leave_type for row in allocations if not leave_unit or get_leave_unit(row.leave_type) == leave_unit]
    if requested_leave_type and requested_leave_type not in candidates:
        frappe.throw(_("The selected leave type does not have an active allocation covering these dates."))
    preferred = employee_values.custom_default_mobile_leave_type if employee_values else None
    if preferred and preferred in candidates:
        candidates = [preferred] + [value for value in candidates if value != preferred]
    balances = []
    for leave_type in candidates:
        if get_leave_unit(leave_type) == "Hours":
            from hr_custom.services.hourly_leave import get_hour_leave_balance
            balance = get_hour_leave_balance(employee, leave_type, from_date).get("remaining_hours", 0)
        else:
            balance = get_leave_balance_on(employee, leave_type, from_date, to_date=to_date, consider_all_leaves_in_the_allocation_period=True)
        if flt(balance) > 0:
            balances.append((flt(balance), leave_type))
    if not balances:
        frappe.throw(_("No leave allocation with an available balance covers {0} to {1}. Please contact HR.").format(from_date, to_date))
    if requested_leave_type:
        if any(item[1] == requested_leave_type for item in balances):
            return requested_leave_type
        frappe.throw(_("The selected leave type has no available balance for these dates."))
    if preferred and any(item[1] == preferred for item in balances):
        return preferred
    return max(balances)[1]


def calculate_leave_calendar(employee, leave_type, from_date, to_date, leave_duration=None, partial_hours=None):
    from hr_custom.services.hourly_leave import calculate_hourly_leave

    start, end = getdate(from_date), getdate(to_date)
    if end < start:
        frappe.throw(_("To Date cannot be before From Date."))
    unit = get_leave_unit(leave_type)
    schedule, source = get_employee_schedule(employee, start)
    holidays = get_holidays(employee, start, getdate(add_days(end, 370)))
    details = []
    current = start
    while current <= end:
        scheduled_hours = flt(schedule.get(current.strftime("%A"), 0), 2)
        is_holiday = current in holidays
        is_working_day = scheduled_hours > 0 and not is_holiday
        details.append({"date": current, "day": current.strftime("%A"), "scheduled_hours": scheduled_hours, "is_holiday": cint(is_holiday), "is_non_working_day": cint(scheduled_hours <= 0), "is_leave_day": cint(is_working_day)})
        current = getdate(add_days(current, 1))

    return_date = getdate(add_days(end, 1))
    for _index in range(370):
        if flt(schedule.get(return_date.strftime("%A"), 0)) > 0 and return_date not in holidays:
            break
        return_date = getdate(add_days(return_date, 1))
    else:
        frappe.throw(_("No return-to-work date could be found in the employee schedule."))

    result = {"leave_type": leave_type, "leave_unit": unit, "schedule_source": source, "return_to_work_date": return_date, "calendar_days": len(details), "working_leave_days": sum(row["is_leave_day"] for row in details), "excluded_days": sum(not row["is_leave_day"] for row in details), "details": details}
    if unit == "Hours":
        result.update(calculate_hourly_leave(employee, leave_type, start, end, leave_duration, partial_hours))
    else:
        include_holiday = cint(frappe.db.get_value("Leave Type", leave_type, "include_holiday"))
        result["leave_days"] = len(details) if include_holiday else result["working_leave_days"]
        if result["leave_days"] <= 0:
            frappe.throw(_("The selected period contains no scheduled working days eligible for leave."))
    return result


@frappe.whitelist()
def get_available_leave_types(from_date=None, to_date=None):
    from hr_custom.api.mobile_attendance import _employee_for_user

    employee = _employee_for_user()
    start, end = getdate(from_date or nowdate()), getdate(to_date or from_date or nowdate())
    allocations = frappe.get_all("Leave Allocation", filters={"employee": employee.name, "docstatus": 1, "from_date": ["<=", start], "to_date": [">=", end]}, fields=["leave_type"], distinct=True, order_by="leave_type asc")
    result = []
    for allocation in allocations:
        unit = get_leave_unit(allocation.leave_type)
        if unit == "Hours":
            from hr_custom.services.hourly_leave import get_hour_leave_balance
            balance = flt(get_hour_leave_balance(employee.name, allocation.leave_type, start).get("remaining_hours", 0), 2)
        else:
            balance = flt(get_leave_balance_on(employee.name, allocation.leave_type, start, to_date=end, consider_all_leaves_in_the_allocation_period=True), 2)
        if balance > 0:
            result.append({"leave_type": allocation.leave_type, "leave_unit": unit, "balance": balance})
    return {"leave_types": result, "has_approver": bool(get_employee_approvers(employee.name)), "employment_type": employee.get("employment_type")}


@frappe.whitelist()
def preview_simple_leave(from_date, to_date, leave_unit="Days", leave_duration=None, partial_hours=None, leave_type=None):
    from hr_custom.api.mobile_attendance import _employee_for_user

    employee = _employee_for_user()
    unit = get_leave_unit(leave_type) if leave_type else (leave_unit if leave_unit in ("Days", "Hours") else None)
    leave_type = select_leave_type(employee.name, getdate(from_date), getdate(to_date), unit, leave_type)
    return calculate_leave_calendar(employee.name, leave_type, from_date, to_date, leave_duration, partial_hours)


@frappe.whitelist(methods=["POST"])
def submit_simple_leave(from_date, to_date, reason, leave_unit="Days", leave_duration=None, partial_hours=None, leave_type=None):
    from hr_custom.api.mobile_attendance import _employee_for_user
    employee = _employee_for_user()
    from_date, to_date = getdate(from_date), getdate(to_date)
    reason = (reason or "").strip()
    if to_date < from_date:
        frappe.throw(_("To Date cannot be before From Date."))
    if not reason:
        frappe.throw(_("Please enter the reason for your leave."))
    approvers = get_employee_approvers(employee.name)
    if not approvers:
        frappe.throw(_("No leave approver is configured for your employee profile. Please contact HR."))
    unit = get_leave_unit(leave_type) if leave_type else (leave_unit if leave_unit in ("Days", "Hours") else None)
    leave_type = select_leave_type(employee.name, from_date, to_date, unit, leave_type)
    unit = get_leave_unit(leave_type)
    preview = calculate_leave_calendar(employee.name, leave_type, from_date, to_date, leave_duration, partial_hours)
    application = frappe.get_doc({"doctype": "Leave Application", "employee": employee.name, "leave_type": leave_type, "from_date": from_date, "to_date": to_date, "posting_date": nowdate(), "description": reason, "leave_approver": approvers[0], "status": "Open", "custom_leave_duration": leave_duration, "custom_partial_hours": partial_hours})
    # This endpoint already binds the application to the authenticated employee.
    # Controlled insertion avoids ESS Company link permissions blocking a valid request.
    application.insert(ignore_permissions=True, ignore_links=True)
    return {"name": application.name, "leave_type": leave_type, "leave_unit": unit, "leave_days": preview.get("leave_days"), "leave_hours": preview.get("total_leave_hours"), "return_to_work_date": preview["return_to_work_date"], "approver": approvers[0], "approver_count": len(approvers), "status": application.status}
