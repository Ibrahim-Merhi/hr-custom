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
	context.full_name = credential.employee_name if context.portal_authenticated else None
	context.body_class = "attendance-app-page"
