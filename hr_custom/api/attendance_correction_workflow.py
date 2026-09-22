"""Hot-loadable correction workflow endpoints.

The production process manager is not always reloadable from a deployment
session. These entry points reload the workflow implementation so lifecycle
fixes are available immediately and remain harmless after the next restart.
"""

import importlib

import frappe


def _modules():
    importlib.reload(importlib.import_module("hr_custom.services.work_schedule"))
    controller = importlib.import_module(
        "hr_custom.hr_custom.doctype.attendance_correction_request.attendance_correction_request"
    )
    service = importlib.import_module("hr_custom.services.attendance_correction")
    portal = importlib.import_module("hr_custom.api.portal_attendance")
    controller = importlib.reload(controller)
    # Frappe caches DocType controller classes separately from Python modules.
    # Remove only this controller so get_doc uses the refreshed lifecycle hooks.
    frappe.controllers.get(frappe.local.site, {}).pop("Attendance Correction Request", None)
    return controller, importlib.reload(service), importlib.reload(portal)


@frappe.whitelist(methods=["POST"])
def submit_attendance_correction(attendance_date, request_type, reason, requested_check_in_time=None, requested_check_out_time=None):
    _, _, portal = _modules()
    return portal.submit_attendance_correction(
        attendance_date,
        request_type,
        reason,
        requested_check_in_time,
        requested_check_out_time,
    )


@frappe.whitelist()
def get_attendance_detail(attendance_date):
    _, _, portal = _modules()
    return portal.get_attendance_detail(attendance_date)


@frappe.whitelist()
def get_correction_detail(name):
    _, _, portal = _modules()
    return portal.get_correction_detail(name)


@frappe.whitelist()
def get_correction_approval_queue():
    _, _, portal = _modules()
    return portal.get_correction_approval_queue()


@frappe.whitelist(methods=["POST"])
def process_correction_approval(name, action, remarks=None):
    _, service, _ = _modules()
    return service.process_correction_approval(name, action, remarks)


@frappe.whitelist(methods=["POST"])
def scan_abnormal_attendance(days=31):
    module = importlib.reload(importlib.import_module("hr_custom.attendance.exceptions"))
    return module.scan_recent_checkins(days)
