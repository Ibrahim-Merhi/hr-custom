from __future__ import annotations

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime
from frappe.utils.password import check_password


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=8, seconds=60)
def login(username=None, password=None):
	username = (username or "").strip().lower()
	password = password or ""
	invalid = _("Invalid portal username or password.")
	if not username or not password:
		frappe.throw(invalid, frappe.AuthenticationError)

	name = frappe.db.get_value("Employee Portal Credential", {"username": username, "enabled": 1}, "name")
	if not name:
		frappe.throw(invalid, frappe.AuthenticationError)
	try:
		check_password(name, password, doctype="Employee Portal Credential", fieldname="password", delete_tracker_cache=False)
	except frappe.AuthenticationError:
		frappe.throw(invalid, frappe.AuthenticationError)

	credential = frappe.get_doc("Employee Portal Credential", name)
	active = frappe.db.get_value("Employee", credential.employee, "status") == "Active"
	user = frappe.db.get_value("User", credential.portal_user, ["enabled", "user_type"], as_dict=True)
	if not active or not user or not user.enabled or user.user_type != "Website User":
		frappe.throw(_("Portal access is disabled. Please contact HR."), frappe.PermissionError)

	frappe.local.login_manager.login_as(credential.portal_user)
	frappe.db.set_value("Employee Portal Credential", credential.name, "last_login", now_datetime(), update_modified=False)
	return {"authenticated": True, "employee": credential.employee, "roles": sorted(row.portal_role for row in credential.roles)}
