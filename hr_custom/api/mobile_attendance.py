import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, get_datetime, getdate, now_datetime, nowdate

from hr_custom.attendance.compat import supported_values
from hr_custom.attendance.geofence import get_distance_in_meters, validate_coordinates
from hr_custom.services.portal_identity import get_portal_employee

LOGGER = frappe.logger("hr_mobile_attendance")


def _request_audit():
    request = getattr(frappe.local, "request", None)
    user_agent = request.headers.get("User-Agent", "") if request else ""
    return user_agent, (getattr(frappe.local, "request_ip", "") or "")


def _settings():
    return frappe.get_cached_doc("HR Mobile Attendance Settings")


def _employee_for_user():
	fields = ["name", "employee_name", "first_name", "branch", "company", "department", "employment_type", "default_shift"]
	meta = frappe.get_meta("Employee")
	for fieldname in ("custom_first_name_ar", "custom_employee_name_ar", "custom_location_not_required"):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	return get_portal_employee(fields=fields)


def _allowed_branches(employee, settings):
    fields = ["name", "custom_enable_mobile_attendance", "custom_branch_latitude", "custom_branch_longitude", "custom_attendance_radius", "custom_max_gps_accuracy", "custom_allow_checkin_without_location"]
    names = []
    if frappe.get_meta("Employee").has_field("custom_attendance_branches"):
        names = frappe.get_all("Employee Attendance Branch", filters={"parent": employee.name, "parenttype": "Employee"}, pluck="branch", order_by="idx asc")
    if not names and employee.branch:
        names = [employee.branch]
    if not names:
        if settings.allow_without_branch:
            return []
        frappe.throw(_("Your employee profile does not have an allowed attendance Branch."))
    rows = frappe.get_all("Branch", filters={"name": ["in", names]}, fields=fields)
    by_name = {row.name: row for row in rows}
    invalid = [name for name in names if name not in by_name or not by_name[name].custom_enable_mobile_attendance]
    if invalid:
        frappe.throw(_("Mobile attendance is not enabled for branch: {0}").format(", ".join(invalid)))
    return [by_name[name] for name in names]


def _select_branch(employee, settings, latitude=None, longitude=None, accuracy=None):
    branches = _allowed_branches(employee, settings)
    if not branches:
        return None, None, None, None, False
    bypass = not cint(settings.require_geolocation) or cint(employee.get("custom_location_not_required"))
    default = next((row for row in branches if row.name == employee.branch), branches[0])
    if latitude in (None, "") or longitude in (None, ""):
        if bypass or default.custom_allow_checkin_without_location:
            return default, None, None, None, False
        frappe.throw(_("A valid GPS location and accuracy are required."))
    try:
        latitude, longitude = validate_coordinates(latitude, longitude)
        accuracy = float(accuracy)
    except (TypeError, ValueError):
        frappe.throw(_("A valid GPS location and accuracy are required."))
    candidates = []
    for branch in branches:
        if branch.custom_branch_latitude is not None and branch.custom_branch_longitude is not None:
            candidates.append((get_distance_in_meters(latitude, longitude, branch.custom_branch_latitude, branch.custom_branch_longitude), branch))
    if not candidates:
        if bypass:
            return default, latitude, longitude, None, False
        frappe.throw(_("The allowed branch locations have not been configured."))
    distance, branch = min(candidates, key=lambda item: item[0])
    if bypass:
        return branch, latitude, longitude, distance, False
    maximum = flt(branch.custom_max_gps_accuracy) or flt(settings.default_max_gps_accuracy)
    radius = flt(branch.custom_attendance_radius) or flt(settings.default_radius)
    if accuracy < 0 or accuracy > maximum:
        frappe.throw(_("GPS accuracy is currently {0} meters. Maximum allowed accuracy is {1} meters.").format(round(accuracy), round(maximum)))
    if distance > radius:
        frappe.throw(_("You are {0} meters away from the nearest allowed branch ({1}). The allowed attendance radius is {2} meters.").format(round(distance), branch.name, round(radius)))
    return branch, latitude, longitude, distance, True


def _latest(employee, attendance_date=None):
    fields = ["name", "log_type", "time", "custom_distance_from_branch", "custom_gps_accuracy"]
    filters = [["employee", "=", employee]]
    if attendance_date:
        filters.extend([
            ["time", ">=", attendance_date],
            ["time", "<", add_days(attendance_date, 1)],
        ])
    rows = frappe.get_all("Employee Checkin", filters=filters, fields=fields, order_by="time desc, creation desc", limit=1)
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
    configuration_error = None
    try:
        branches = _allowed_branches(employee, settings)
    except frappe.ValidationError as error:
        # Keep the rest of the employee portal usable when attendance setup is
        # incomplete. Check-in submission retains strict branch validation.
        branches = []
        configuration_error = str(error)
    latest = _latest(employee.name, getdate(timestamp))
    branch = next((row for row in branches if row.name == employee.branch), branches[0] if branches else None)
    radius = (flt(branch.custom_attendance_radius) if branch else 0) or flt(settings.default_radius)
    maximum_accuracy = (flt(branch.custom_max_gps_accuracy) if branch else 0) or flt(settings.default_max_gps_accuracy)
    require_location = cint(settings.require_geolocation) and not cint(employee.get("custom_location_not_required")) and not cint(branch.custom_allow_checkin_without_location if branch else 0)
    return {"employee": employee.name, "employee_name": employee.employee_name, "first_name": employee.first_name, "custom_first_name_ar": employee.get("custom_first_name_ar"), "custom_employee_name_ar": employee.get("custom_employee_name_ar"), "branch": branch.name if branch else None, "allowed_branches": [row.name for row in branches], "configuration_error": configuration_error, "server_time": timestamp, "current_state": "CHECKED IN" if latest and latest.log_type == "IN" else "CHECKED OUT", "next_action": "OUT" if latest and latest.log_type == "IN" else "IN", "last_checkin": latest, "branch_location_enabled": bool(branch), "attendance_radius": radius, "maximum_gps_accuracy": maximum_accuracy, "require_geolocation": require_location, "location_cache_seconds": cint(settings.location_cache_seconds) or 120, "fast_location_timeout": cint(settings.fast_location_timeout) or 5, "high_accuracy_timeout": cint(settings.high_accuracy_timeout) or 12, "portal_tabs": {"attendance": cint(settings.show_attendance_tab), "leaves": cint(settings.show_leaves_tab), "salary": cint(settings.show_salary_tab), "profile": cint(settings.show_profile_tab)}}


@frappe.whitelist()
def get_attendance_history(limit=10):
    employee = _employee_for_user()
    limit = max(1, min(cint(limit) or 10, 30))
    return frappe.get_list("Employee Checkin", filters={"employee": employee.name}, fields=["name", "log_type", "time", "custom_checkin_source", "custom_distance_from_branch"], order_by="time desc", limit=limit)


@frappe.whitelist()
def mark_portal_notification_read(notification):
    """Mark only the authenticated employee's selected notification as read."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to view notifications."), frappe.PermissionError)
    from hr_custom.services.portal_identity import get_effective_approval_user
    owner = frappe.db.get_value("PWA Notification", notification, "to_user")
    if not owner or owner != get_effective_approval_user():
        frappe.throw(_("Notification not found."), frappe.PermissionError)
    frappe.db.set_value("PWA Notification", notification, "read", 1, update_modified=False)
    return {"name": notification, "read": 1}


def _owned_portal_notification(notification):
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to manage notifications."), frappe.PermissionError)
    from hr_custom.services.portal_identity import get_effective_approval_user
    owner = frappe.db.get_value("PWA Notification", notification, "to_user")
    if not owner or owner != get_effective_approval_user():
        frappe.throw(_("Notification not found."), frappe.PermissionError)
    return notification


@frappe.whitelist(methods=["POST"])
def archive_portal_notification(notification):
    notification = _owned_portal_notification(notification)
    frappe.db.set_value("PWA Notification", notification, {"custom_archived": 1, "read": 1}, update_modified=False)
    return {"name": notification, "archived": 1}


@frappe.whitelist(methods=["POST"])
def unarchive_portal_notification(notification):
    notification = _owned_portal_notification(notification)
    frappe.db.set_value("PWA Notification", notification, "custom_archived", 0, update_modified=False)
    return {"name": notification, "archived": 0}


@frappe.whitelist(methods=["POST"])
def delete_portal_notification(notification):
    notification = _owned_portal_notification(notification)
    frappe.delete_doc("PWA Notification", notification, ignore_permissions=True)
    return {"name": notification, "deleted": 1}


def _validated_period(from_date=None, to_date=None):
    end = getdate(to_date or nowdate())
    start = getdate(from_date or add_months(end, -1))
    if end < start:
        frappe.throw(_("To Date cannot be before From Date."))
    if (end - start).days > 366:
        frappe.throw(_("Please select a period of one year or less."))
    return start, end


@frappe.whitelist()
def get_attendance_period(from_date=None, to_date=None):
    employee = _employee_for_user()
    start, end = _validated_period(from_date, to_date)
    # Employee identity comes only from the authenticated session. get_all is
    # intentional: ESS users may not have standard Desk read permission for
    # Attendance, while this endpoint always restricts results to themselves.
    rows = frappe.get_all("Attendance", filters={"employee": employee.name, "attendance_date": ["between", [start, end]], "docstatus": 1}, fields=["name", "employee", "attendance_date", "status", "in_time", "out_time", "working_hours", "late_entry", "early_exit"], order_by="attendance_date desc", limit=370)
    official_dates = {getdate(row.attendance_date) for row in rows}
    punches = frappe.get_all("Employee Checkin", filters={"employee": employee.name, "time": ["between", [start, add_days(end, 1)]], "attendance": ["is", "not set"]}, fields=["name", "time", "log_type"], order_by="time asc")
    by_date = {}
    for punch in punches:
        date = getdate(punch.time)
        if date not in official_dates:
            by_date.setdefault(date, []).append(punch)
    for date, logs in by_date.items():
        first_in = next((log.time for log in logs if log.log_type == "IN"), None)
        last_out = next((log.time for log in reversed(logs) if log.log_type == "OUT"), None)
        hours = max(0, (last_out - first_in).total_seconds() / 3600) if first_in and last_out and last_out > first_in else 0
        rows.append({"name": None, "employee": employee.name, "attendance_date": date, "status": _("Pending"), "in_time": first_in, "out_time": last_out, "working_hours": hours, "late_entry": 0, "early_exit": 0, "is_pending": 1})
    # ``frappe.get_all`` returns frappe._dict rows, while the pending rows
    # assembled above are regular dictionaries. Access through ``get`` so a
    # period containing both official attendance and pending punches can be
    # sorted without raising AttributeError and leaving the portal spinner on.
    return sorted(rows, key=lambda row: getdate(row.get("attendance_date")), reverse=True)


@frappe.whitelist()
def get_leave_portal_data():
    from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
    employee = _employee_for_user()
    today = getdate(nowdate())
    allocations = frappe.get_all("Leave Allocation", filters={"employee": employee.name, "docstatus": 1, "from_date": ["<=", today], "to_date": [">=", today]}, fields=["leave_type", "total_leaves_allocated", "from_date", "to_date"], order_by="leave_type asc")
    balances = []
    for allocation in allocations:
        remaining = max(0, flt(get_leave_balance_on(employee.name, allocation.leave_type, today, consider_all_leaves_in_the_allocation_period=True), 2))
        allocated = flt(allocation.total_leaves_allocated, 2)
        balances.append({"leave_type": allocation.leave_type, "allocated": allocated, "used": max(0, flt(allocated - remaining, 2)), "remaining": remaining, "from_date": allocation.from_date, "to_date": allocation.to_date})
    requests = frappe.get_all("Leave Application", filters={"employee": employee.name, "docstatus": ["<", 2]}, fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status", "description", "custom_approval_stage"], order_by="creation desc", limit=30)
    return {"balances": balances, "requests": requests}


def _can_review_leave(doc, user):
    from hr_custom.services.simple_leave import _is_hr_manager
    from hr_custom.services.portal_identity import get_effective_approval_user
    own_employee = _employee_for_user().name
    return doc.employee == own_employee or doc.custom_current_approver == get_effective_approval_user(user) or _is_hr_manager(user)


@frappe.whitelist()
def get_portal_leave_detail(name):
    doc = frappe.get_doc("Leave Application", name)
    if not _can_review_leave(doc, frappe.session.user):
        frappe.throw(_("You are not permitted to view this leave request."), frappe.PermissionError)
    return {
        "name": doc.name, "employee": doc.employee, "employee_name": doc.employee_name,
        "leave_type": doc.leave_type, "from_date": doc.from_date, "to_date": doc.to_date,
        "total_leave_days": doc.total_leave_days, "description": doc.description,
        "status": doc.status, "stage": doc.custom_approval_stage,
        "current_approver": doc.custom_current_approver,
        "steps": [{"approver": row.approver, "approver_name": row.approver_name, "sequence": row.sequence, "status": row.status, "acted_on": row.acted_on, "remarks": row.remarks} for row in doc.custom_approval_steps],
    }


@frappe.whitelist()
def get_leave_approval_queue():
    from hr_custom.services.simple_leave import _is_hr_manager
    from hr_custom.services.portal_identity import get_effective_approval_user, has_portal_role
    user = get_effective_approval_user()
    is_hr = _is_hr_manager()
    fields = ["name", "employee", "employee_name", "leave_type", "from_date", "to_date", "total_leave_days", "description", "status", "custom_approval_stage", "creation"]
    rows = frappe.get_all("Leave Application", filters={"docstatus": 0, "custom_approval_stage": "Pending Approver Approval", "custom_current_approver": user}, fields=fields, order_by="creation asc", limit=100)
    for row in rows:
        row.review_mode = "approver"
    if is_hr:
        final_rows = frappe.get_all("Leave Application", filters={"docstatus": 0, "custom_approval_stage": "Pending HR Approval"}, fields=fields, order_by="creation asc", limit=100)
        for row in final_rows:
            row.review_mode = "hr"
        rows.extend(final_rows)
        rows.sort(key=lambda row: row.creation)
    configured = has_portal_role("Leave Approver") and frappe.db.exists("Employee Leave Approver", {"approver": user, "enabled": 1})
    return {"items": rows, "can_review": bool(is_hr or configured)}


@frappe.whitelist()
def get_salary_portal_data():
    employee = _employee_for_user()
    return frappe.get_list("Salary Slip", filters={"employee": employee.name, "docstatus": 1}, fields=["name", "start_date", "end_date", "currency", "gross_pay", "total_deduction", "net_pay"], order_by="end_date desc", limit=12)


@frappe.whitelist()
def get_profile_data():
    employee = _employee_for_user()
    fields = ["name", "employee_name", "first_name", "custom_first_name_ar", "custom_employee_name_ar", "middle_name", "last_name", "gender", "date_of_birth", "company", "department", "designation", "branch", "grade", "reports_to", "date_of_joining", "employment_type", "holiday_list", "cell_number", "personal_email", "company_email", "prefered_contact_email", "image"]
    meta = frappe.get_meta("Employee")
    available = [field for field in fields if field == "name" or meta.has_field(field)]
    result = frappe.db.get_value("Employee", employee.name, available, as_dict=True)
    result["salary"] = frappe.get_all("Salary Slip", filters={"employee": employee.name, "docstatus": 1}, fields=["currency", "gross_pay", "total_deduction", "net_pay", "end_date"], order_by="end_date desc", limit=1)
    return result


@frappe.whitelist(methods=["POST"])
def set_portal_language(language):
    if language not in ("en", "ar"):
        frappe.throw(_("Only English and Arabic are supported in the employee portal."))
    from hr_custom.services.portal_identity import get_portal_credential
    credential = get_portal_credential(required=True)
    frappe.db.set_value("Employee Portal Credential", credential.name, "language", language, update_modified=False)
    return {"language": language}


@frappe.whitelist()
def get_portal_notifications(limit=30, include_archived=0):
    employee = _employee_for_user()
    limit = max(1, min(cint(limit) or 30, 100))
    from hr_custom.services.portal_identity import get_effective_approval_user
    filters = {"to_user": get_effective_approval_user()}
    if not cint(include_archived):
        filters["custom_archived"] = 0
    rows = frappe.get_all("PWA Notification", filters=filters, fields=["name", "message", "reference_document_type", "reference_document_name", "read", "custom_archived", "creation"], order_by="creation desc", limit=limit)
    announcement_names = [row.reference_document_name for row in rows if row.reference_document_type == "HR Announcement"]
    announcements = {
        row.name: row
        for row in frappe.get_all(
            "HR Announcement",
            filters={"name": ["in", announcement_names]},
            fields=["name", "title", "message"],
        )
    } if announcement_names else {}
    leave_names = [row.reference_document_name for row in rows if row.reference_document_type == "Leave Application" and row.reference_document_name]
    own_leaves = set(frappe.get_all("Leave Application", filters={"name": ["in", leave_names], "employee": employee.name}, pluck="name")) if leave_names else set()
    for row in rows:
        row.is_own_record = row.reference_document_type != "Leave Application" or row.reference_document_name in own_leaves
        if row.reference_document_type == "HR Announcement" and row.reference_document_name in announcements:
            announcement = announcements[row.reference_document_name]
            row.title = announcement.title
            row.body = announcement.message
            row.category = "announcements"
        else:
            row.title = row.reference_document_type or _("HR Update")
            row.body = row.message
            row.category = "leaves" if row.reference_document_type == "Leave Application" else "updates"
        if cint(row.custom_archived):
            row.category = "archived"
    return {"items": rows, "unread": sum(not cint(row.read) and not cint(row.custom_archived) for row in rows), "push_enabled": bool(frappe.db.get_single_value("Push Notification Settings", "enable_push_notification_relay")), "relay_url": frappe.conf.get("push_relay_server_url")}


@frappe.whitelist(methods=["POST"])
def mark_portal_notifications_read():
    _employee_for_user()
    from hr_custom.services.portal_identity import get_effective_approval_user
    frappe.db.set_value("PWA Notification", {"to_user": get_effective_approval_user(), "read": 0}, "read", 1, update_modified=False)
    return {"success": True}


@frappe.whitelist(methods=["POST"])
def submit_checkin(latitude=None, longitude=None, accuracy=None, device_info=None, device_id=None, request_id=None):
    settings = _settings()
    if not settings.enable_mobile_attendance:
        frappe.throw(_("Mobile attendance is disabled."))
    employee, timestamp = _employee_for_user(), now_datetime()
    branch, latitude, longitude, distance, geofence_validated = _select_branch(employee, settings, latitude, longitude, accuracy)
    _validate_device(employee, settings, device_id, timestamp)
    frappe.db.sql("select name from `tabEmployee` where name=%s for update", employee.name)
    latest = _latest(employee.name, getdate(timestamp))
    action = "OUT" if latest and latest.log_type == "IN" else "IN"
    if latest and abs((timestamp - latest.time).total_seconds()) < 10:
        frappe.throw(_("Your previous attendance action is still being processed. Please wait a few seconds."))
    user_agent, ip_address = _request_audit()
    values = {"employee": employee.name, "log_type": action, "time": timestamp, "device_id": (device_id or "")[:140], "custom_branch": branch.name if branch else None, "custom_latitude": latitude, "custom_longitude": longitude, "custom_gps_accuracy": flt(accuracy) if accuracy not in (None, "") else None, "custom_distance_from_branch": distance, "custom_checkin_source": "Mobile GPS", "custom_device_info": (device_info or "")[:500] if settings.enable_device_audit else "", "custom_user_agent": user_agent[:500] if settings.enable_device_audit else "", "custom_ip_address": ip_address[:140] if settings.enable_ip_audit else "", "custom_server_timestamp": timestamp, "custom_geofence_validated": cint(geofence_validated), "custom_validation_message": "Inside configured branch geofence" if geofence_validated else "Location bypass allowed by policy"}
    # Standard Employee Checkin validation assigns the applicable HRMS shift.
    # HRMS auto-attendance is the sole owner of Attendance and late/early flags.
    doc = frappe.get_doc({"doctype": "Employee Checkin", **supported_values("Employee Checkin", values)})
    doc.insert(ignore_permissions=True)
    # HRMS processes a completed shift only after Last Sync passes its actual
    # end. Mobile punches are themselves the synchronization source, so advance
    # this marker monotonically whenever a punch is assigned to a shift.
    if doc.shift:
        last_sync = frappe.db.get_value("Shift Type", doc.shift, "last_sync_of_checkin")
        if not last_sync or get_datetime(last_sync) < timestamp:
            frappe.db.set_value("Shift Type", doc.shift, "last_sync_of_checkin", timestamp, update_modified=False)
    # The portal's current attendance policy treats any valid same-day IN → OUT
    # pair as Present. Call the idempotent finalizer explicitly so mobile users
    # do not have to wait for HRMS shift synchronization or a scheduler cycle.
    # The Employee Checkin hook remains responsible for punches entered in Desk.
    if action == "OUT":
        from hr_custom.services.portal_attendance_processing import finalize_completed_day

        finalize_completed_day(employee.name, getdate(timestamp))
    return {"name": doc.name, "action": action, "time": doc.time, "distance": round(distance or 0, 1), "accuracy": round(flt(accuracy), 1), "state": "CHECKED IN" if action == "IN" else "CHECKED OUT"}
