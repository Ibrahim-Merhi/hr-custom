from __future__ import annotations

import frappe
from frappe import _


def get_portal_credential(user=None, required=False):
	user = user or frappe.session.user
	name = None if user == "Guest" else frappe.db.get_value(
		"Employee Portal Credential", {"portal_user": user, "enabled": 1}, "name"
	)
	if not name:
		if required:
			frappe.throw(_("Please sign in with your Employee Portal credentials."), frappe.PermissionError)
		return None
	return frappe.get_doc("Employee Portal Credential", name)


def get_portal_roles(user=None):
	credential = get_portal_credential(user)
	return {row.portal_role for row in credential.roles} if credential else set()


def has_portal_role(role, user=None):
	return role in get_portal_roles(user)


def get_portal_employee(user=None, fields=None):
	credential = get_portal_credential(user, required=True)
	fields = fields or ["name", "employee_name"]
	employee = frappe.db.get_value("Employee", credential.employee, fields, as_dict=True)
	if not employee or frappe.db.get_value("Employee", credential.employee, "status") != "Active":
		frappe.throw(_("Your linked Employee is not active. Please contact HR."), frappe.PermissionError)
	return employee


def get_effective_approval_user(user=None):
	credential = get_portal_credential(user)
	if not credential:
		return user or frappe.session.user
	return frappe.db.get_value("Employee", credential.employee, "user_id") or credential.portal_user
