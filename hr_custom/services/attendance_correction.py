import frappe
from frappe import _
from frappe.share import add_docshare
from frappe.utils import now_datetime

from hr_custom.services.simple_leave import _hr_managers, _is_hr_manager, get_employee_approvers


def initialize_correction_approval(doc):
    if doc.get("approval_steps"):
        return
    if frappe.db.get_single_value("HR Mobile Attendance Settings", "send_corrections_directly_to_hr"):
        doc.approval_stage = "Pending HR Approval"
        doc.status = "Pending HR Approval"
        doc.current_approver = None
        doc.approver = None
        return
    approvers = get_employee_approvers(doc.employee)
    for sequence, approver in enumerate(approvers, 1):
        doc.append("approval_steps", {"approver": approver, "sequence": sequence, "status": "Pending"})
    doc.approval_stage = "Pending Approver Approval" if approvers else "Pending HR Approval"
    doc.status = doc.approval_stage
    doc.current_approver = approvers[0] if approvers else None
    doc.approver = doc.current_approver


def ensure_direct_hr_routing_event():
    """Install a dynamic guard so the setting works before worker reloads too."""
    name = "Route Attendance Corrections Directly to HR"
    values = {
        "script_type": "DocType Event",
        "reference_doctype": "Attendance Correction Request",
        "doctype_event": "Before Insert",
        "disabled": 0,
        "script": """if frappe.db.get_single_value('HR Mobile Attendance Settings', 'send_corrections_directly_to_hr'):\n    doc.set('approval_steps', [])\n    doc.approval_stage = 'Pending HR Approval'\n    doc.status = 'Pending HR Approval'\n    doc.current_approver = None\n    doc.approver = None""",
    }
    if frappe.db.exists("Server Script", name):
        server_script = frappe.get_doc("Server Script", name)
        server_script.update(values)
        server_script.save(ignore_permissions=True)
    else:
        server_script = frappe.get_doc({"doctype": "Server Script", "name": name, **values})
        server_script.insert(ignore_permissions=True)
    frappe.cache.delete_value("server_script_map")
    return server_script.name


def _notify(user, doc, message):
    if not user:
        return
    notification = frappe.new_doc("PWA Notification")
    notification.from_user = frappe.session.user
    notification.to_user = user
    notification.message = message
    notification.reference_document_type = doc.doctype
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


def notify_current_reviewer(doc):
    for approver in get_employee_approvers(doc.employee):
        _share_with_reviewer(doc, approver)
    if doc.approval_stage == "Pending Approver Approval":
        _notify(doc.current_approver, doc, _("Attendance correction {0} is waiting for your approval.").format(doc.name))
    elif doc.approval_stage == "Pending HR Approval":
        for user in _hr_managers():
            _notify(user, doc, _("Attendance correction {0} is waiting for final HR approval.").format(doc.name))


def get_correction_context(doc):
    user = frappe.session.user
    is_hr = _is_hr_manager(user)
    is_current = doc.approval_stage == "Pending Approver Approval" and doc.current_approver == user
    return {
        "can_act": bool(doc.docstatus < 2 and doc.approval_stage in ("Pending Approver Approval", "Pending HR Approval") and (is_current or is_hr)),
        "is_hr": is_hr,
        "is_hr_override": bool(is_hr and doc.approval_stage == "Pending Approver Approval" and not is_current),
        "is_final_hr_step": doc.approval_stage == "Pending HR Approval",
    }


@frappe.whitelist(methods=["POST"])
def process_correction_approval(name, action, remarks=None):
    if action not in ("approve", "reject"):
        frappe.throw(_("Invalid approval action."))
    frappe.db.sql("select name from `tabAttendance Correction Request` where name=%s for update", name)
    doc = frappe.get_doc("Attendance Correction Request", name)
    if doc.docstatus == 2 or doc.approval_stage not in ("Pending Approver Approval", "Pending HR Approval"):
        frappe.throw(_("This correction request is no longer waiting for approval."))

    user = frappe.session.user
    is_hr = _is_hr_manager(user)
    is_current_approver = doc.approval_stage == "Pending Approver Approval" and doc.current_approver == user
    # A configured approver acts in the approver capacity first, even when that
    # user also has an HR role. Final HR approval is a separate second action.
    is_override = is_hr and doc.approval_stage == "Pending Approver Approval" and not is_current_approver
    if not is_hr and doc.current_approver != user:
        frappe.throw(_("This request is waiting for another approver."), frappe.PermissionError)
    note = (remarks or "").strip()
    if is_override and not note:
        frappe.throw(_("An HR override note is required when approver steps are bypassed."))

    current_step = next((row for row in doc.approval_steps if row.status == "Pending" and row.approver == user), None)
    if current_step:
        current_step.status = "Approved" if action == "approve" else "Rejected"
        current_step.acted_on = now_datetime()
        current_step.remarks = note

    if action == "reject":
        doc.approval_stage = "Rejected"
        doc.status = "Rejected"
        doc.current_approver = None
        doc.approved_by = user
        doc.approval_date = now_datetime()
        doc.remarks = note
        doc.flags.ignore_permissions = True
        if doc.docstatus == 1:
            doc.flags.ignore_validate_update_after_submit = True
        doc.save()
        return doc

    if is_hr and (doc.approval_stage == "Pending HR Approval" or is_override):
        if is_override:
            doc.hr_override_note = note
            for step in doc.approval_steps:
                if step.status == "Pending":
                    step.status = "Skipped"
                    step.acted_on = now_datetime()
                    step.remarks = _("Bypassed by HR: {0}").format(note)
        doc.approval_stage = "Approved"
        doc.status = "Approved"
        doc.current_approver = None
        doc.approved_by = user
        doc.approval_date = now_datetime()
        doc.remarks = note
        doc.flags.ignore_permissions = True
        if doc.docstatus == 1:
            doc.flags.ignore_validate_update_after_submit = True
        doc.save()
        if doc.docstatus == 0:
            doc.flags.ignore_permissions = True
            doc.submit()
        from hr_custom.hr_custom.doctype.attendance_correction_request.attendance_correction_request import apply
        return apply(doc.name)

    next_step = next((row for row in sorted(doc.approval_steps, key=lambda row: (row.sequence, row.idx)) if row.status == "Pending"), None)
    if next_step:
        doc.current_approver = next_step.approver
        doc.approver = next_step.approver
    else:
        doc.approval_stage = "Pending HR Approval"
        doc.status = "Pending HR Approval"
        doc.current_approver = None
        doc.approver = None
    doc.flags.ignore_permissions = True
    if doc.docstatus == 1:
        doc.flags.ignore_validate_update_after_submit = True
    doc.save()
    notify_current_reviewer(doc)
    return doc
