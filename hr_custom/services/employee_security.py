import frappe
from frappe import _
from frappe.utils import cint


LOCATION_BYPASS_FIELD = "custom_location_not_required"
LOCATION_BYPASS_ROLES = {"System Manager"}


def can_manage_location_bypass(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool(LOCATION_BYPASS_ROLES.intersection(frappe.get_roles(user)))


def validate_location_bypass_permission(doc, method=None):
	"""Prevent non-system users from changing the employee GPS bypass through any API."""
	previous = doc.get_doc_before_save()
	previous_value = cint(previous.get(LOCATION_BYPASS_FIELD)) if previous else 0
	current_value = cint(doc.get(LOCATION_BYPASS_FIELD))

	if previous_value != current_value and not can_manage_location_bypass():
		frappe.throw(
			_("Only Administrator or a System Manager can change Location Not Required."),
			frappe.PermissionError,
		)
