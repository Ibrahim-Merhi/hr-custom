import frappe


def execute():
    values = {
        "enable_employee_portal": 1,
        "show_attendance_tab": 1,
        "show_leaves_tab": 1,
        "show_salary_tab": 1,
        "show_profile_tab": 1,
        "show_settings_tab": 1,
        "location_cache_seconds": 120,
        "fast_location_timeout": 5,
        "high_accuracy_timeout": 12,
        "notify_salary_slip_submission": 1,
    }
    for fieldname, value in values.items():
        frappe.db.set_single_value("HR Mobile Attendance Settings", fieldname, value)
