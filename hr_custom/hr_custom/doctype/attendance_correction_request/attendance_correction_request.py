import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

HR_ROLES = {"HR Manager", "System Manager"}


class AttendanceCorrectionRequest(Document):
    def before_insert(self):
        from hr_custom.services.attendance_correction import initialize_correction_approval

        initialize_correction_approval(self)

    def after_insert(self):
        from hr_custom.services.attendance_correction import notify_current_reviewer

        notify_current_reviewer(self)

    def validate(self):
        roles = set(frappe.get_roles())
        from hr_custom.services.portal_identity import get_portal_credential, has_portal_role
        if not HR_ROLES.intersection(roles) and not has_portal_role("HR"):
            if not frappe.db.get_single_value("HR Mobile Attendance Settings", "allow_employee_correction_request"):
                frappe.throw(_("Employee correction requests are disabled."))
            credential = get_portal_credential()
            own = credential.employee if credential else None
            if not own or self.employee != own:
                frappe.throw(_("You may only request a correction for yourself."), frappe.PermissionError)
        for value in (self.requested_check_in_time, self.requested_check_out_time):
            if value and getdate(value) != getdate(self.attendance_date):
                frappe.throw(_("Requested check-in and check-out must be on the attendance date."))
        if self.request_type in ("Wrong Check In", "Wrong Check Out") and not self.original_checkin:
            frappe.throw(_("Original Checkin is required for a wrong-time correction."))
        if self.request_type in ("Missing Check In", "Wrong Check In") and not self.requested_check_in_time:
            frappe.throw(_("Requested Check In Time is required."))
        if self.request_type in ("Missing Check Out", "Wrong Check Out") and not self.requested_check_out_time:
            frappe.throw(_("Requested Check Out Time is required."))

    def before_submit(self):
        if self.status != "Approved" or self.approval_stage != "Approved":
            frappe.throw(_("Only a correction request with final HR approval can be submitted."))

    def on_submit(self):
        pass


def _require_hr():
    from hr_custom.services.portal_identity import has_portal_role
    if not HR_ROLES.intersection(frappe.get_roles()) and not has_portal_role("HR"):
        frappe.throw(_("Only HR Manager or System Manager can perform this action."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def approve(name, remarks=None):
    from hr_custom.services.attendance_correction import process_correction_approval

    return process_correction_approval(name, "approve", remarks)


@frappe.whitelist(methods=["POST"])
def reject(name, remarks=None):
    from hr_custom.services.attendance_correction import process_correction_approval

    return process_correction_approval(name, "reject", remarks)


@frappe.whitelist(methods=["POST"])
def apply(name):
    _require_hr()
    doc = frappe.get_doc("Attendance Correction Request", name)
    if doc.docstatus != 1:
        frappe.throw(_("The approved request must be submitted before it can be applied."))
    if doc.status not in ("Approved", "Applied"):
        frappe.throw(_("The request must be approved before it can be applied."))
    if doc.status == "Applied":
        _rebuild_attendance(doc)
        return frappe.get_doc("Attendance Correction Request", name)
    if doc.original_checkin and doc.request_type.startswith("Wrong"):
        original = frappe.get_doc("Employee Checkin", doc.original_checkin)
        if original.employee != doc.employee:
            frappe.throw(_("Original Checkin does not belong to this employee."))
        original.db_set("skip_auto_attendance", 1)
        original.add_comment("Info", _("Excluded from Auto Attendance by correction request {0}.").format(doc.name))
    events = []
    if doc.requested_check_in_time: events.append(("IN", doc.requested_check_in_time))
    if doc.requested_check_out_time: events.append(("OUT", doc.requested_check_out_time))
    for log_type, timestamp in events:
        if frappe.db.exists("Employee Checkin", {"employee": doc.employee, "time": timestamp, "log_type": log_type, "custom_correction_request": doc.name}):
            continue
        frappe.get_doc({"doctype": "Employee Checkin", "employee": doc.employee, "time": timestamp, "log_type": log_type, "custom_checkin_source": "Manual HR", "custom_server_timestamp": now_datetime(), "custom_validation_message": _("Created from approved correction request {0}").format(doc.name), "custom_correction_request": doc.name}).insert(ignore_permissions=True)
    doc.db_set({"status": "Applied", "approval_stage": "Applied"})
    _rebuild_attendance(doc)
    for exception in frappe.get_all("Attendance Exception", filters={"employee": doc.employee, "attendance_date": doc.attendance_date, "status": "Open"}, pluck="name"):
        frappe.db.set_value("Attendance Exception", exception, {"status": "Resolved", "resolved_by": frappe.session.user, "resolved_on": now_datetime(), "resolution_notes": _("Resolved by correction request {0}").format(doc.name)})
    return frappe.get_doc("Attendance Correction Request", name)


def _rebuild_attendance(doc):
    """Apply the same temporary IN/OUT rule used by normal punches."""
    from hr_custom.services.portal_attendance_processing import finalize_completed_day
    return finalize_completed_day(doc.employee, doc.attendance_date)
