from __future__ import annotations

import hashlib
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime


PORTAL_COOKIE = "hr_portal_token"
PORTAL_USER_PREFIX = "portal::"
# Current browsers cap persistent cookies at roughly 400 days. Refreshing this
# window on authenticated requests provides durable sign-in without asking
# browsers to accept an out-of-range Max-Age value.
PORTAL_COOKIE_MAX_AGE = 400 * 24 * 60 * 60


def token_hash(token: str) -> str:
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _cookie_token():
	request = getattr(frappe.local, "request", None)
	return request.cookies.get(PORTAL_COOKIE) if request else None


def set_portal_cookie(token):
	request = getattr(frappe.local, "request", None)
	forwarded_proto = request.headers.get("X-Forwarded-Proto", "") if request else ""
	secure = bool(request and (request.scheme == "https" or forwarded_proto.split(",", 1)[0].strip() == "https"))
	frappe.local.cookie_manager.set_cookie(
		PORTAL_COOKIE, token, max_age=PORTAL_COOKIE_MAX_AGE,
		httponly=True, secure=secure, samesite="Lax",
	)


def get_portal_session(required=False, renew=True):
	cached = getattr(frappe.local, "employee_portal_session", None)
	if cached:
		return cached
	token = _cookie_token()
	row = None
	if token:
		row = frappe.db.get_value(
			"Employee Portal Session",
			{"token_hash": token_hash(token), "revoked": 0},
			["name", "credential", "last_seen", "is_impersonation", "impersonated_by", "impersonation_reason", "expires_on"], as_dict=True,
		)
		if row and row.expires_on and get_datetime(row.expires_on) <= now_datetime():
			frappe.db.set_value("Employee Portal Session", row.name, "revoked", 1, update_modified=False)
			row = None
		if row and not frappe.db.get_value("Employee Portal Credential", row.credential, "enabled"):
			row = None
	if not row:
		if required:
			frappe.throw(_("Your portal session is no longer active. Please sign in again."), frappe.AuthenticationError)
		return None
	frappe.local.employee_portal_session = row
	# Sliding persistence: every valid visit renews the browser-supported
	# lifetime. The server token itself remains valid until explicitly revoked.
	if renew:
		set_portal_cookie(token)
	if not row.last_seen or (now_datetime() - get_datetime(row.last_seen)).total_seconds() > 300:
		frappe.db.set_value("Employee Portal Session", row.name, "last_seen", now_datetime(), update_modified=False)
	return row


def get_portal_credential(user=None, required=False):
	cached = getattr(frappe.local, "employee_portal_credential", None)
	if cached and (not user or user in (frappe.session.user, f"{PORTAL_USER_PREFIX}{cached.name}")):
		return cached
	if user and user not in ("Guest", frappe.session.user) and not str(user).startswith(PORTAL_USER_PREFIX):
		return None
	session = get_portal_session(required=required)
	if not session:
		return None
	credential = frappe.get_doc("Employee Portal Credential", session.credential)
	frappe.local.employee_portal_credential = credential
	return credential


def authenticate_portal_request():
	"""Authenticate hr_custom API calls with an independent portal token."""
	request = getattr(frappe.local, "request", None)
	if not request:
		return
	command = (request.args.get("cmd") or getattr(frappe.local.form_dict, "cmd", "") or "").strip()
	path_command = request.path.removeprefix("/api/method/") if request.path.startswith("/api/method/") else ""
	command = command or path_command
	if not command.startswith("hr_custom."):
		return
	if command in {
		"hr_custom.api.portal_auth.login",
		"hr_custom.api.portal_auth.logout",
		"hr_custom.api.portal_auth.stop_impersonation",
	}:
		return
	credential = get_portal_credential()
	if credential:
		form_dict = frappe.local.form_dict
		frappe.set_user(f"{PORTAL_USER_PREFIX}{credential.name}")
		frappe.local.form_dict = form_dict
		frappe.local.employee_portal_credential = credential


def get_portal_roles(user=None):
	credential = get_portal_credential(user)
	roles = {row.portal_role for row in credential.roles} if credential else set()
	if "Portal Administrator" in roles:
		roles.update({"Employee", "Leave Approver", "HR"})
	return roles


def has_portal_role(role, user=None):
	return role in get_portal_roles(user)


def get_portal_employee(user=None, fields=None):
	credential = get_portal_credential(user, required=True)
	if credential.account_type == "Portal Administrator" or not credential.employee:
		frappe.throw(_("This Portal Administrator account is not linked to an Employee profile."), frappe.PermissionError)
	fields = fields or ["name", "employee_name"]
	employee = frappe.db.get_value("Employee", credential.employee, fields, as_dict=True)
	if not employee or frappe.db.get_value("Employee", credential.employee, "status") != "Active":
		frappe.throw(_("Your linked Employee is not active. Please contact HR."), frappe.PermissionError)
	return employee


def get_effective_approval_user(user=None):
	credential = get_portal_credential(user)
	if not credential:
		return user or frappe.session.user
	return (frappe.db.get_value("Employee", credential.employee, "user_id") if credential.account_type != "Portal Administrator" and credential.employee else None) or f"{PORTAL_USER_PREFIX}{credential.name}"


@contextmanager
def run_portal_document_as_system_user():
	"""Run standard DocType lifecycle code without exposing a fake portal User.

	Portal authentication deliberately uses a virtual identity rather than a
	Frappe User record. Some standard ERPNext/HRMS controllers load the current
	User while validating a document. The calling endpoint must authenticate and
	bind the employee before entering this narrowly scoped context.
	"""
	original_user = frappe.session.user
	if not str(original_user).startswith(PORTAL_USER_PREFIX):
		yield
		return

	form_dict = frappe.local.form_dict
	try:
		frappe.set_user("Administrator")
		frappe.local.form_dict = form_dict
		yield
	finally:
		frappe.set_user(original_user)
		frappe.local.form_dict = form_dict
