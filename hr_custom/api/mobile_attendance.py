import json

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from hr_custom.attendance.compat import supported_values
from hr_custom.attendance.geofence import get_distance_in_meters, validate_coordinates
from hr_custom.attendance.shift import resolve_shift, timing_flags

LOGGER = frappe.logger("hr_mobile_attendance")


def _employee_for_user():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to use mobile attendance."), frappe.PermissionError)
    rows = frappe.get_all("Employee", filters={"user_id": frappe.session.user, "status": "Active"}, fields=["name", "employee_name", "branch", "company", "department", "default_shift"], limit=2)
    if not rows:
        frappe.throw(_("No active Employee is linked to your user account."), frappe.PermissionError)
    if len(rows) > 1:
        LOGGER.error("Multiple active employees mapped to user %s", frappe.session.user)
        frappe.throw(_("Multiple active Employees are linked to your user account. Please contact HR."))
    if not rows[0].branch:
        frappe.throw(_("Your employee profile does not have a Branch."))
    return rows[0]


def _branch(employee):
    branch = frappe.db.get_value("Branch", employee.branch, ["name", "custom_enable_mobile_attendance", "custom_branch_latitude", "custom_branch_longitude", "custom_attendance_radius", "custom_max_gps_accuracy", "custom_allow_checkin_without_location"], as_dict=True)
    if not branch or not branch.custom_enable_mobile_attendance:
        frappe.throw(_("Mobile attendance is not enabled for your branch."))
    if branch.custom_branch_latitude is None or branch.custom_branch_longitude is None:
        frappe.throw(_("The branch location has not been configured."))
    return branch


def _latest(employee):
    return frappe.get_all("Employee Checkin", filters={"employee": employee}, fields=["name", "log_type", "time", "custom_distance_from_branch", "custom_gps_accuracy"], order_by="time desc, creation desc", limit=1)


@frappe.whitelist()
def get_status():
    employee, timestamp = _employee_for_user(), now_datetime()
    branch, latest = _branch(employee), _latest(employee.name)
    shift = resolve_shift(employee.name, timestamp)
    return {
        "employee": employee.name, "employee_name": employee.employee_name, "branch": branch.name,
        "server_time": timestamp, "shift": shift.name if shift else None,
        "shift_start": shift.start if shift else None, "shift_end": shift.end if shift else None,
        "current_state": "CHECKED IN" if latest and latest[0].log_type == "IN" else "CHECKED OUT",
        "next_action": "OUT" if latest and latest[0].log_type == "IN" else "IN",
        "last_checkin": latest[0] if latest else None, "branch_location_enabled": 1,
        "attendance_radius": branch.custom_attendance_radius,
    }


@frappe.whitelist(methods=["POST"])
def submit_checkin(latitude=None, longitude=None, accuracy=None, device_info=None, request_id=None):
    employee, timestamp = _employee_for_user(), now_datetime()
    branch = _branch(employee)
    try:
        latitude, longitude = validate_coordinates(latitude, longitude)
        accuracy = float(accuracy)
    except (TypeError, ValueError):
        frappe.throw(_("A valid GPS location and accuracy are required."))
    if accuracy < 0:
        frappe.throw(_("GPS accuracy is invalid."))
    if accuracy > flt(branch.custom_max_gps_accuracy):
        frappe.throw(_("GPS accuracy is currently {0} meters. Maximum allowed accuracy is {1} meters.").format(round(accuracy), round(flt(branch.custom_max_gps_accuracy))))
    distance = get_distance_in_meters(latitude, longitude, branch.custom_branch_latitude, branch.custom_branch_longitude)
    if distance > flt(branch.custom_attendance_radius):
        frappe.throw(_("You are {0} meters away from {1}. The allowed attendance radius is {2} meters.").format(round(distance), branch.name, round(flt(branch.custom_attendance_radius))))

    # Serialize per employee. The second state read occurs after acquiring the DB lock.
    frappe.db.sql("select name from `tabEmployee` where name=%s for update", employee.name)
    latest = _latest(employee.name)
    action = "OUT" if latest and latest[0].log_type == "IN" else "IN"
    if latest and abs((timestamp - latest[0].time).total_seconds()) < 10:
        frappe.throw(_("Your previous attendance action is still being processed. Please wait a few seconds."))
    shift = resolve_shift(employee.name, timestamp)
    flags = timing_flags(shift, timestamp, action)
    values = {
        "employee": employee.name, "log_type": action, "time": timestamp,
        "custom_branch": branch.name, "custom_latitude": latitude, "custom_longitude": longitude,
        "custom_gps_accuracy": accuracy, "custom_distance_from_branch": distance,
        "custom_checkin_source": "Mobile GPS", "custom_device_info": (device_info or "")[:500],
        "custom_user_agent": (frappe.get_request_header("User-Agent") or "")[:500],
        "custom_ip_address": (frappe.local.request_ip or "")[:140],
        "custom_server_timestamp": timestamp, "custom_geofence_validated": 1,
        "custom_validation_message": "Inside configured branch geofence",
        "custom_shift_type": shift.name if shift else None,
        "custom_is_late": flags["is_late"], "custom_minutes_late": flags["minutes_late"],
        "custom_is_early_exit": flags["is_early_exit"], "custom_minutes_early": flags["minutes_early"],
    }
    doc = frappe.get_doc({"doctype": "Employee Checkin", **supported_values("Employee Checkin", values)})
    doc.insert(ignore_permissions=True)
    return {"name": doc.name, "action": action, "time": doc.time, "distance": round(distance, 1), "accuracy": round(accuracy, 1), "state": "CHECKED IN" if action == "IN" else "CHECKED OUT"}

