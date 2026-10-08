import frappe


def execute():
	frappe.db.set_single_value(
		"HR Mobile Attendance Settings", "send_corrections_directly_to_hr", 1
	)
