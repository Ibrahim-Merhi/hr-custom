app_name="hr_custom"
app_title="HR Custom"
app_publisher="Custom"
app_description="Secure mobile GPS attendance"
app_email="admin@example.com"
app_license="MIT"
required_apps=["erpnext","hrms"]
auth_hooks=["hr_custom.services.portal_identity.authenticate_portal_request"]
fixtures=[{"dt":"Property Setter","filters":[["doc_type","=","Employee"]]}]
override_doctype_class={
    "Leave Application":"hr_custom.overrides.leave_application.HourlyLeaveApplication",
    "Leave Allocation":"hr_custom.overrides.leave_allocation.HourlyLeaveAllocation",
    "PWA Notification":"hr_custom.overrides.pwa_notification.CustomPWANotification",
}
doctype_js={
    "Leave Application":"public/js/hourly_leave_application.js",
    "Employment Type":"public/js/work_schedule.js",
    "Employee":["public/js/work_schedule.js", "public/js/employee_bilingual_name.js"],
}
before_install="hr_custom.install.before_install"
before_migrate="hr_custom.install.before_migrate"
# Custom fields reference DocTypes shipped by this app. Run their setup only
# after Frappe has completed model, fixture, and customization synchronization.
after_sync="hr_custom.install.after_sync"
after_migrate="hr_custom.install.after_migrate"
before_uninstall="hr_custom.install.before_uninstall"
doc_events={
    "Attendance":{"validate":"hr_custom.services.attendance_branches.populate_attendance_branches"},
    "Employee Checkin":{"after_insert":"hr_custom.services.portal_attendance_processing.finalize_checkin_pair"},
    "Branch":{"validate":"hr_custom.attendance.validation.validate_branch"},
    "Employment Type":{"validate":"hr_custom.services.work_schedule.validate_schedule_document"},
    "Employee":{"validate":["hr_custom.services.work_schedule.validate_schedule_document", "hr_custom.services.employee_name.apply_bilingual_name", "hr_custom.services.simple_leave.validate_employee_leave_setup"]},
    "Weekly Work Schedule":{"validate":"hr_custom.services.work_schedule.validate_schedule_document"},
    "Salary Slip":{"on_submit":"hr_custom.services.portal_notifications.notify_salary_slip_available"},
    "Leave Application":{
        "before_insert":"hr_custom.services.simple_leave.initialize_leave_approval",
        "after_insert":"hr_custom.services.simple_leave.notify_leave_workflow",
    },
}
# HRMS owns auto-attendance. This scheduler only creates custom exception alerts.
scheduler_events={
    "hourly":["hr_custom.attendance.exceptions.scan_recent_checkins", "hr_custom.services.portal_attendance_processing.reconcile_recent_completed_pairs"],
    "daily":["hr_custom.api.portal_auth.cleanup_expired_sessions"],
}
website_route_rules=[{"from_route":"/attendance","to_route":"mobile-attendance"}]
permission_query_conditions={
    "Attendance Correction Request":"hr_custom.permissions.correction_query",
    "Attendance Exception":"hr_custom.permissions.exception_query",
    "Employee Attendance Device":"hr_custom.permissions.device_query",
    "Employee Checkin":"hr_custom.permissions.checkin_query",
}
has_permission={
    "Attendance Correction Request":"hr_custom.permissions.own_employee_permission",
    "Attendance Exception":"hr_custom.permissions.exception_permission",
    "Employee Attendance Device":"hr_custom.permissions.own_employee_permission",
    "Employee Checkin":"hr_custom.permissions.own_employee_permission",
}
