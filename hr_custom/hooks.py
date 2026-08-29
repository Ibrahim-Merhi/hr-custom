app_name="hr_custom"
app_title="HR Custom"
app_publisher="Custom"
app_description="Secure mobile GPS attendance"
app_email="admin@example.com"
app_license="MIT"
required_apps=["erpnext","hrms"]
after_install="hr_custom.install.after_install"
after_migrate="hr_custom.install.after_migrate"
before_uninstall="hr_custom.install.before_uninstall"
doc_events={"Branch":{"validate":"hr_custom.attendance.validation.validate_branch"}}
scheduler_events={"hourly":["hr_custom.attendance.processor.process_pending_attendance"],"daily":["hr_custom.attendance.processor.finalize_previous_day"]}
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
