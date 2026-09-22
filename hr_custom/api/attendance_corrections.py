"""Fresh entry points for attendance-correction portal features.

Production Gunicorn workers can retain an older ``portal_attendance`` module.
This module has a new import path, so every worker loads it on first request and
refreshes the implementation module when the correction methods are missing.
"""

import importlib

import frappe


def _implementation():
    module = importlib.import_module("hr_custom.api.portal_attendance")
    if not hasattr(module, "get_correction_approval_queue"):
        module = importlib.reload(module)
    return module


@frappe.whitelist()
def get_attendance_detail(attendance_date):
    return _implementation().get_attendance_detail(attendance_date)


@frappe.whitelist(methods=["POST"])
def submit_attendance_correction(attendance_date, request_type, reason, requested_check_in_time=None, requested_check_out_time=None):
    return _implementation().submit_attendance_correction(
        attendance_date,
        request_type,
        reason,
        requested_check_in_time,
        requested_check_out_time,
    )


@frappe.whitelist()
def get_correction_detail(name):
    return _implementation().get_correction_detail(name)


@frappe.whitelist()
def get_correction_approval_queue():
    return _implementation().get_correction_approval_queue()
