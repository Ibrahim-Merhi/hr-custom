import frappe

HR_ROLES = {"HR User", "HR Manager", "System Manager"}


def _is_hr(user):
    from hr_custom.services.portal_identity import has_portal_role
    if has_portal_role("HR", user):
        return True
    return bool(HR_ROLES.intersection(frappe.get_roles(user)))


def employee_for_user(user=None):
    from hr_custom.services.portal_identity import get_portal_credential
    credential = get_portal_credential(user)
    if credential:
        return credential.employee
    return frappe.db.get_value("Employee", {"user_id": user or frappe.session.user, "status": "Active"}, "name")


def employee_condition(user=None, employee_field="employee"):
    user = user or frappe.session.user
    if user == "Administrator" or _is_hr(user):
        return ""
    employee = employee_for_user(user)
    return f"`tab{{doctype}}`.`{employee_field}`={frappe.db.escape(employee)}" if employee else "1=0"


def correction_query(user=None):
    return employee_condition(user).format(doctype="Attendance Correction Request")


def device_query(user=None):
    return employee_condition(user).format(doctype="Employee Attendance Device")


def checkin_query(user=None):
    return employee_condition(user).format(doctype="Employee Checkin")


def exception_query(user=None):
    user = user or frappe.session.user
    return "" if user == "Administrator" or _is_hr(user) else "1=0"


def own_employee_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if user == "Administrator" or _is_hr(user):
        return True
    if permission_type not in (None, "read", "create", "write", "submit"):
        return False
    return bool(doc.employee and doc.employee == employee_for_user(user))


def exception_permission(doc, user=None, permission_type=None):
    return bool((user or frappe.session.user) == "Administrator" or _is_hr(user or frappe.session.user))
