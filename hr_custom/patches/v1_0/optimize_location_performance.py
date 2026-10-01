import frappe


def execute():
    frappe.db.set_single_value(
        "HR Mobile Attendance Settings",
        {
            "location_cache_seconds": 60,
            "fast_location_timeout": 2,
            "high_accuracy_timeout": 5,
        },
    )
