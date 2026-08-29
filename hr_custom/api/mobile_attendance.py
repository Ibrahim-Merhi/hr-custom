import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

from hr_custom.attendance.compat import supported_values
from hr_custom.attendance.geofence import get_distance_in_meters, validate_coordinates
from hr_custom.attendance.shift import resolve_shift, timing_flags

LOGGER = frappe.logger("hr_mobile_attendance")


def _settings():
    return frappe.get_single("HR Mobile Attendance Settings")


def _employee_for_user():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to use mobile attendance."), frappe.PermissionError)
    rows = frappe.get_all("Employee", filters={"user_id": frappe.session.user, "status": "Active"}, fields=["name", "employee_name", "branch", "company", "department", "default_shift"], limit=2)
    if not rows:
        frappe.throw(_("No active Employee is linked to your user account."), frappe.PermissionError)
    if len(rows) > 1:
        LOGGER.error("Multiple active employees mapped to user %s", frappe.session.user)
        frappe.throw(_("Multiple active Employees are linked to your user account. Please contact HR."))
    return rows[0]


def _branch(employee, settings):
    if not employee.branch:
        if settings.allow_without_branch:
            return None
        frappe.throw(_("Your employee profile does not have a Branch."))
    fields = ["name", "custom_enable_mobile_attendance", "custom_branch_latitude", "custom_branch_longitude", "custom_attendance_radius", "custom_max_gps_accuracy", "custom_allow_checkin_without_location"]
    branch = frappe.db.get_value("Branch", employee.branch, fields, as_dict=True)
    if not branch or not branch.custom_enable_mobile_attendance:
        frappe.throw(_("Mobile attendance is not enabled for your branch."))
    if settings.require_geolocation and not branch.custom_allow_checkin_without_location and (branch.custom_branch_latitude is None or branch.custom_branch_longitude is None):
        frappe.throw(_("The branch location has not been configured."))
    return branch


def _latest(employee):
    fields = ["name", "log_type", "time", "custom_distance_from_branch", "custom_gps_accuracy"]
    rows = frappe.get_all("Employee Checkin", filters={"employee": employee}, fields=fields, order_by="time desc, creation desc", limit=1)
    return rows[0] if rows else None


def _validate_location(branch, settings, latitude, longitude, accuracy):
    if not settings.require_geolocation or (branch and branch.custom_allow_checkin_without_location and latitude in (None, "")):
        return None, None, None, False
    try:
        latitude, longitude = validate_coordinates(latitude, longitude)
        accuracy = float(accuracy)
    except (TypeError, ValueError):
        frappe.throw(_("A valid GPS location and accuracy are required."))
    if accuracy < 0:
        frappe.throw(_("GPS accuracy is invalid."))
    maximum = flt(branch.custom_max_gps_accuracy) or flt(settings.default_max_gps_accuracy)
    radius = flt(branch.custom_attendance_radius) or flt(settings.default_radius)
    if accuracy > maximum:
        frappe.throw(_("GPS accuracy is currently {0} meters. Maximum allowed accuracy is {1} meters.").format(round(accuracy), round(maximum)))
    distance = get_distance_in_meters(latitude, longitude, branch.custom_branch_latitude, branch.custom_branch_longitude)
    if distance > radius:
        frappe.throw(_("You are {0} meters away from {1}. The allowed attendance radius is {2} meters.").format(round(distance), branch.name, round(radius)))
    return latitude, longitude, distance, True


def _validate_device(employee, settings, device_id, timestamp):
    if not settings.require_registered_device:
        return
    if not device_id:
        frappe.throw(_("A registered attendance device is required."))
    registered = frappe.db.get_value("Employee Attendance Device", {"employee": employee.name, "device_id": device_id, "active": 1}, "name")
    if not registered:
        frappe.throw(_("This device is not registered for mobile attendance."))
    frappe.db.set_value("Employee Attendance Device", registered, "last_used", timestamp, update_modified=False)


@frappe.whitelist()
def get_status():
    settings = _settings()
    if not settings.enable_mobile_attendance:
        frappe.throw(_("Mobile attendance is disabled."))
    employee, timestamp = _employee_for_user(), now_datetime()
    branch, latest = _branch(employee, settings), _latest(employee.name)
    shift = resolve_shift(employee.name, timestamp)
    radius = (flt(branch.custom_attendance_radius) if branch else 0) or flt(settings.default_radius)
    return {"employee": employee.name, "employee_name": employee.employee_name, "branch": branch.name if branch else None, "server_time": timestamp, "shift": shift.name if shift else None, "shift_start": shift.start if shift else None, "shift_end": shift.end if shift else None, "current_state": "CHECKED IN" if latest and latest.log_type == "IN" else "CHECKED OUT", "next_action": "OUT" if latest and latest.log_type == "IN" else "IN", "last_checkin": latest, "branch_location_enabled": bool(branch), "attendance_radius": radius}


@frappe.whitelist(methods=["POST"])
def submit_checkin(latitude=None, longitude=None, accuracy=None, device_info=None, device_id=None, request_id=None):
    settings = _settings()
    if not settings.enable_mobile_attendance:
        frappe.throw(_("Mobile attendance is disabled."))
    employee, timestamp = _employee_for_user(), now_datetime()
    branch = _branch(employee, settings)
    latitude, longitude, distance, geofence_validated = _validate_location(branch, settings, latitude, longitude, accuracy)
    _validate_device(employee, settings, device_id, timestamp)
    frappe.db.sql("select name from `tabEmployee` where name=%s for update", employee.name)
    latest = _latest(employee.name)
    action = "OUT" if latest and latest.log_type == "IN" else "IN"
    if latest and abs((timestamp - latest.time).total_seconds()) < 10:
        frappe.throw(_("Your previous attendance action is still being processed. Please wait a few seconds."))
    shift = resolve_shift(employee.name, timestamp)
    if settings.require_shift and not shift:
        frappe.throw(_("No active shift is assigned to you."))
    if settings.enforce_checkin_window and not shift:
        frappe.throw(_("Attendance is currently outside the allowed shift window."))
    if not shift and not settings.allow_without_shift:
        frappe.throw(_("No active shift is assigned to you."))
    flags = timing_flags(shift, timestamp, action)
    values = {"employee": employee.name, "log_type": action, "time": timestamp, "device_id": (device_id or "")[:140], "custom_branch": branch.name if branch else None, "custom_latitude": latitude, "custom_longitude": longitude, "custom_gps_accuracy": flt(accuracy) if accuracy not in (None, "") else None, "custom_distance_from_branch": distance, "custom_checkin_source": "Mobile GPS", "custom_device_info": (device_info or "")[:500] if settings.enable_device_audit else "", "custom_user_agent": (frappe.get_request_header("User-Agent") or "")[:500] if settings.enable_device_audit else "", "custom_ip_address": (frappe.local.request_ip or "")[:140] if settings.enable_ip_audit else "", "custom_server_timestamp": timestamp, "custom_geofence_validated": cint(geofence_validated), "custom_validation_message": "Inside configured branch geofence" if geofence_validated else "Location bypass allowed by policy", "custom_shift_type": shift.name if shift else None, "custom_is_late": flags["is_late"] if settings.enable_late_tracking else 0, "custom_minutes_late": flags["minutes_late"] if settings.enable_late_tracking else 0, "custom_is_early_exit": flags["is_early_exit"] if settings.enable_early_exit_tracking else 0, "custom_minutes_early": flags["minutes_early"] if settings.enable_early_exit_tracking else 0}
    doc = frappe.get_doc({"doctype": "Employee Checkin", **supported_values("Employee Checkin", values)})
    doc.insert(ignore_permissions=True)
    return {"name": doc.name, "action": action, "time": doc.time, "distance": round(distance or 0, 1), "accuracy": round(flt(accuracy), 1), "state": "CHECKED IN" if action == "IN" else "CHECKED OUT"}
