import importlib

import frappe


def _api():
    import hr_custom.api.mobile_attendance as mobile_attendance
    return importlib.reload(mobile_attendance)


@frappe.whitelist()
def get_status():
    return _api().get_status()


@frappe.whitelist(methods=["POST"])
def submit_checkin(latitude=None, longitude=None, accuracy=None, device_info=None, device_id=None, request_id=None):
    return _api().submit_checkin(latitude, longitude, accuracy, device_info, device_id, request_id)
