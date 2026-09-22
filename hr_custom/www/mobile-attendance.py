import frappe

from hr_custom.services.portal_identity import get_portal_credential

no_cache = 1


def get_context(context):
	credential = get_portal_credential()
	if credential and credential.language in ("en", "ar"):
		frappe.local.lang = credential.language
	context.no_breadcrumbs = True
	context.title = frappe._("Attendance")
	context.is_guest = not credential
	context.session_user = None if context.is_guest else frappe.session.user
	context.full_name = None if context.is_guest else credential.employee_name
	context.body_class = "attendance-app-page"
