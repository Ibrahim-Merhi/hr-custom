"""Data-free rolling refresh helper for preloaded attendance API workers."""

import importlib

import frappe


@frappe.whitelist(allow_guest=True)
def ensure_current_api():
    """Make legacy attendance routes available in the serving web worker."""
    module = importlib.import_module("hr_custom.api.portal_attendance")
    required = (
        "get_attendance_detail",
        "submit_attendance_correction",
        "get_correction_detail",
        "get_correction_approval_queue",
    )
    if not all(hasattr(module, method) for method in required):
        module = importlib.reload(module)

    return {"ready": all(hasattr(module, method) for method in required)}
