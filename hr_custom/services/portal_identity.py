from __future__ import annotations

import hashlib

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


def get_portal_session(required=False):
	cached = getattr(frappe.local, "employee_portal_session", None)
	if cached:
		return cached
	token = _cookie_token()
	row = None
	if token:
		row = frappe.db.get_value(
			"Employee Portal Session",
			{"token_hash": token_hash(token), "revoked": 0},
			["name", "credential", "last_seen"], as_dict=True,
		)
		if row and not frappe.db.get_value("Employee Portal Credential", row.credential, "enabled"):
			row = None
	if not row:
		if required:
			frappe.throw(_("Your portal session is no longer active. Please sign in again."), frappe.AuthenticationError)
		return None
	frappe.local.employee_portal_session = row
	# Sliding persistence: every valid visit renews the browser-supported
	# lifetime. The server token itself remains valid until explicitly revoked.
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
	if not request or not request.path.startswith("/api/method/hr_custom."):
		return
	credential = get_portal_credential()
	if credential:
		form_dict = frappe.local.form_dict
		frappe.set_user(f"{PORTAL_USER_PREFIX}{credential.name}")
		frappe.local.form_dict = form_dict
		frappe.local.employee_portal_credential = credential


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
	return frappe.db.get_value("Employee", credential.employee, "user_id") or f"{PORTAL_USER_PREFIX}{credential.name}"
