import frappe

no_cache = 1


def get_context(context):
    context.no_breadcrumbs = True
    context.title = frappe._("Attendance")
    context.is_guest = frappe.session.user == "Guest"
    context.session_user = None if context.is_guest else frappe.session.user
    context.full_name = None if context.is_guest else frappe.utils.get_fullname(frappe.session.user)
    context.body_class = "attendance-app-page"

