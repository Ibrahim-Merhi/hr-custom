"""Data-free rolling refresh for approval workflow services."""

import importlib

import frappe


@frappe.whitelist(allow_guest=True)
def ensure_current_workflow():
    """Load the server-side sharing fix in the web worker serving this call."""
    correction = importlib.import_module("hr_custom.services.attendance_correction")
    leave = importlib.import_module("hr_custom.services.simple_leave")
    if not hasattr(correction, "_share_with_reviewer"):
        correction = importlib.reload(correction)
    if not hasattr(leave, "_share_with_reviewer"):
        leave = importlib.reload(leave)
    return {
        "ready": hasattr(correction, "_share_with_reviewer")
        and hasattr(leave, "_share_with_reviewer")
    }
