from __future__ import annotations

import hmac
import secrets

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime
from frappe.utils.password import check_password, get_decrypted_password, update_password
from hr_custom.services.portal_identity import PORTAL_COOKIE, PORTAL_USER_PREFIX, get_portal_credential, get_portal_session, set_portal_cookie, token_hash


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


def cleanup_revoked_sessions():
	"""Remove sessions that were explicitly revoked by logout or access changes."""
	frappe.db.delete("Employee Portal Session", {"revoked": 1})


# Backwards-compatible scheduler target for installations upgraded in place.
cleanup_expired_sessions = cleanup_revoked_sessions


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
	if frappe.db.get_value("Employee", credential.employee, "status") != "Active":
		frappe.throw(_("Portal access is disabled. Please contact HR."), frappe.PermissionError)
	# Keep a small, auditable number of active devices per employee.
	active_sessions = frappe.get_all(
		"Employee Portal Session", filters={"credential": credential.name, "revoked": 0},
		pluck="name", order_by="last_seen desc", limit_page_length=100,
	)
	for old_session in active_sessions[4:]:
		frappe.db.set_value("Employee Portal Session", old_session, "revoked", 1, update_modified=False)

	raw_token = secrets.token_urlsafe(32)
	request = getattr(frappe.local, "request", None)
	frappe.get_doc({
		"doctype": "Employee Portal Session", "credential": credential.name,
		"token_hash": token_hash(raw_token),
		"last_seen": now_datetime(), "ip_address": getattr(frappe.local, "request_ip", "") or "",
		"user_agent": request.headers.get("User-Agent", "")[:500] if request else "",
	}).insert(ignore_permissions=True)
	set_portal_cookie(raw_token)
	frappe.db.set_value("Employee Portal Credential", credential.name, "last_login", now_datetime(), update_modified=False)
	return {"authenticated": True, "employee": credential.employee, "roles": sorted(row.portal_role for row in credential.roles)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def logout():
	session = get_portal_session(renew=False)
	if session:
		frappe.db.set_value("Employee Portal Session", session.name, "revoked", 1, update_modified=False)
	frappe.local.cookie_manager.delete_cookie(PORTAL_COOKIE)
	return {"logged_out": True}


@frappe.whitelist()
def subscribe_portal_push(fcm_token, project_name="hrms"):
	"""Register notifications against the authenticated portal identity."""
	from frappe.push_notification import PushNotification

	credential = get_portal_credential(required=True)
	success, message = PushNotification(project_name).add_token(
		f"{PORTAL_USER_PREFIX}{credential.name}", fcm_token
	)
	return {"success": success, "message": message}
