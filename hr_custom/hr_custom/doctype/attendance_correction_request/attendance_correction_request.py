import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

HR_ROLES = {"HR Manager", "System Manager"}


class AttendanceCorrectionRequest(Document):
    def validate(self):
        roles = set(frappe.get_roles())
        if not HR_ROLES.intersection(roles):
            if not frappe.db.get_single_value("HR Mobile Attendance Settings", "allow_employee_correction_request"):
                frappe.throw(_("Employee correction requests are disabled."))
            own = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")
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

    def on_submit(self):
        self.db_set("status", "Pending Approval", update_modified=False)


def _require_hr():
    if not HR_ROLES.intersection(frappe.get_roles()):
        frappe.throw(_("Only HR Manager or System Manager can perform this action."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def approve(name, remarks=None):
    _require_hr()
    doc = frappe.get_doc("Attendance Correction Request", name)
    if doc.docstatus != 1 or doc.status != "Pending Approval":
        frappe.throw(_("Only a submitted pending request can be approved."))
    doc.db_set({"status": "Approved", "approved_by": frappe.session.user, "approval_date": now_datetime(), "remarks": remarks or doc.remarks})
    apply(name)
    return frappe.get_doc("Attendance Correction Request", name)


@frappe.whitelist(methods=["POST"])
def reject(name, remarks=None):
    _require_hr()
    doc = frappe.get_doc("Attendance Correction Request", name)
    if doc.docstatus != 1 or doc.status != "Pending Approval":
        frappe.throw(_("Only a submitted pending request can be rejected."))
    doc.db_set({"status": "Rejected", "approved_by": frappe.session.user, "approval_date": now_datetime(), "remarks": remarks or doc.remarks})
    return doc


@frappe.whitelist(methods=["POST"])
def apply(name):
    _require_hr()
    doc = frappe.get_doc("Attendance Correction Request", name)
    if doc.status not in ("Approved", "Applied"):
        frappe.throw(_("The request must be approved before it can be applied."))
    if doc.status == "Applied":
        return doc
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
    doc.db_set("status", "Applied")
    for exception in frappe.get_all("Attendance Exception", filters={"employee": doc.employee, "attendance_date": doc.attendance_date, "status": "Open"}, pluck="name"):
        frappe.db.set_value("Attendance Exception", exception, {"status": "Resolved", "resolved_by": frappe.session.user, "resolved_on": now_datetime(), "resolution_notes": _("Resolved by correction request {0}").format(doc.name)})
    return frappe.get_doc("Attendance Correction Request", name)
