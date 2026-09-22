from __future__ import annotations

import hmac

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime
from frappe.utils.password import check_password, get_decrypted_password, update_password


def upgrade_legacy_portal_passwords():
	"""Convert portal passwords created by the first release to one-way hashes."""
	converted = 0
	for name in frappe.get_all("Employee Portal Credential", pluck="name"):
		legacy_password = get_decrypted_password(
			"Employee Portal Credential", name, "password", raise_exception=False
		)
		if legacy_password:
			update_password(name, legacy_password, doctype="Employee Portal Credential", fieldname="password")
			converted += 1
	return converted


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=8, seconds=60)
def login(username=None, password=None):
	username = (username or "").strip()
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
		# Credentials created by the first release used Frappe's encrypted
		# Password-field storage. Accept them once and replace them with a
		# one-way hash immediately.
		legacy_password = get_decrypted_password(
			"Employee Portal Credential", name, "password", raise_exception=False
		)
		if not legacy_password or not hmac.compare_digest(legacy_password, password):
			frappe.throw(invalid, frappe.AuthenticationError)
		update_password(name, password, doctype="Employee Portal Credential", fieldname="password")

	credential = frappe.get_doc("Employee Portal Credential", name)
	active = frappe.db.get_value("Employee", credential.employee, "status") == "Active"
	user = frappe.db.get_value("User", credential.portal_user, ["enabled", "user_type"], as_dict=True)
	if not active or not user or not user.enabled or user.user_type != "Website User":
		frappe.throw(_("Portal access is disabled. Please contact HR."), frappe.PermissionError)

	frappe.local.login_manager.login_as(credential.portal_user)
	frappe.db.set_value("Employee Portal Credential", credential.name, "last_login", now_datetime(), update_modified=False)
	return {"authenticated": True, "employee": credential.employee, "roles": sorted(row.portal_role for row in credential.roles)}
