import json

import frappe
from frappe.translate import get_translations_from_apps

from hr_custom.services.portal_identity import get_portal_credential

no_cache = 1


def get_context(context):
	credential = get_portal_credential()
	if credential and credential.language in ("en", "ar"):
		frappe.local.lang = credential.language
	portal_language = credential.language if credential and credential.language in ("en", "ar") else "en"
	context.portal_language = portal_language
	context.portal_language_json = json.dumps(portal_language)
	context.portal_messages_json = json.dumps(get_translations_from_apps(portal_language, apps=["hr_custom"]), ensure_ascii=False)
	context.no_breadcrumbs = True
	context.title = frappe._("Attendance")
	context.portal_authenticated = bool(credential)
	context.session_user = frappe.session.user if context.portal_authenticated else None
	context.full_name = None
	if context.portal_authenticated:
		fields = ["first_name", "employee_name"]
		meta = frappe.get_meta("Employee")
		for fieldname in ("custom_first_name_ar", "custom_employee_name_ar"):
			if meta.has_field(fieldname):
				fields.append(fieldname)
		employee = frappe.db.get_value("Employee", credential.employee, fields, as_dict=True)
		if employee:
			context.full_name = (
				employee.get("custom_first_name_ar") or employee.first_name or employee.get("custom_employee_name_ar") or employee.employee_name
				if portal_language == "ar"
				else employee.first_name or employee.employee_name or employee.get("custom_first_name_ar") or employee.get("custom_employee_name_ar")
			)
	context.body_class = "attendance-app-page"
