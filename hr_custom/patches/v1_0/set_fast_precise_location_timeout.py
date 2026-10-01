import frappe


def execute():
    frappe.db.set_single_value(
        "HR Mobile Attendance Settings",
        "high_accuracy_timeout",
        5,
    )
