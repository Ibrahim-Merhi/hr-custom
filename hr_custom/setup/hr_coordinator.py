from __future__ import annotations

import frappe

ROLE = "HR Coordinator"
VISIBLE_PERMISSION_FIELDS = ("select", "read", "report", "export", "print")


def ensure_hr_coordinator_permissions():
    """Keep HR Coordinator visibility aligned with HR User without core edits."""
    _ensure_role()
    doctypes = _hr_user_doctypes()
    doctypes.update({"Company", "Branch", "Department", "Designation", "Employment Type", "Employee Grade"})
    doctypes.update(frappe.get_all("DocType", filters={"module": "HR Custom", "istable": 0}, pluck="name", limit_page_length=0))
    for doctype in sorted(doctypes):
        if frappe.db.exists("DocType", doctype):
            _upsert_read_permission(doctype)
    _copy_hr_user_role_links()
    frappe.clear_cache()


def _ensure_role():
    if not frappe.db.exists("Role", ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert(ignore_permissions=True)
    else:
        frappe.db.set_value("Role", ROLE, {"disabled": 0, "desk_access": 1}, update_modified=False)


def _hr_user_doctypes():
    result = set()
    for table in ("DocPerm", "Custom DocPerm"):
        result.update(frappe.get_all(table, filters={"role": "HR User", "read": 1}, pluck="parent", limit_page_length=0))
    return result


def _upsert_read_permission(doctype):
    filters = {"parent": doctype, "role": ROLE, "permlevel": 0, "if_owner": 0}
    name = frappe.db.get_value("Custom DocPerm", filters, "name")
    values = {fieldname: 1 for fieldname in VISIBLE_PERMISSION_FIELDS}
    if name:
        frappe.db.set_value("Custom DocPerm", name, values, update_modified=False)
        return
    frappe.get_doc({
        "doctype": "Custom DocPerm",
        "parent": doctype,
        "parenttype": "DocType",
        "parentfield": "permissions",
        "role": ROLE,
        "permlevel": 0,
        "if_owner": 0,
        **values,
    }).insert(ignore_permissions=True)


def _copy_hr_user_role_links():
    rows = frappe.get_all(
        "Has Role",
        filters={"role": "HR User", "parenttype": ["in", ["Report", "Workspace", "Dashboard", "Page"]]},
        fields=["parent", "parenttype", "parentfield"],
        limit_page_length=0,
    )
    for row in rows:
        values = {"parent": row.parent, "parenttype": row.parenttype, "parentfield": row.parentfield, "role": ROLE}
        if not frappe.db.exists("Has Role", values):
            frappe.get_doc({"doctype": "Has Role", **values}).insert(ignore_permissions=True)
