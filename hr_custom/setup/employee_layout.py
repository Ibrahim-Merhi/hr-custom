import json

import frappe


ONE_COLUMN_BREAKS = {
    "custom_column_break_arrzi",  # Leave Approval
    "column_break_9",             # Leave Approval
    "column_break1",              # Leave Approval
    "column_break_25",            # Work Schedule
    "column_break_18",            # Empty trailing Work Schedule column
}

MOBILE_ATTENDANCE_FIELDS = [
    "custom_mobile_attendance_policy",
    "custom_location_not_required",
    "custom_attendance_branches",
]

EMPLOYEE_HISTORY_FIELDS = [
    "custom_leave_balances_tab",
    "custom_leave_balances_html",
    "custom_attendance_log_tab",
    "custom_attendance_log_html",
]

LEAVE_POLICY_FIELDS = ["custom_leave_calculation_mode_override"]


def apply_employee_layout():
    """Preserve the customized Employee overview with full-width HR sections."""
    setter = frappe.db.get_value(
        "Property Setter",
        {"doc_type": "Employee", "property": "field_order"},
        ["name", "value"],
        as_dict=True,
    )
    if setter and setter.value:
        order = json.loads(setter.value)
        order = [fieldname for fieldname in order if fieldname not in ONE_COLUMN_BREAKS]
        order = [fieldname for fieldname in order if fieldname not in MOBILE_ATTENDANCE_FIELDS]
        order = [fieldname for fieldname in order if fieldname not in LEAVE_POLICY_FIELDS]
        leave_anchor = order.index("custom_default_mobile_leave_type") + 1
        order[leave_anchor:leave_anchor] = LEAVE_POLICY_FIELDS
        anchor = order.index("custom_leave_approvers") + 1
        order[anchor:anchor] = MOBILE_ATTENDANCE_FIELDS
        order = [fieldname for fieldname in order if fieldname not in EMPLOYEE_HISTORY_FIELDS]
        history_anchor = order.index("holiday_list") + 1
        order[history_anchor:history_anchor] = EMPLOYEE_HISTORY_FIELDS
        order = _merge_personal_and_contacts(order)
        frappe.db.set_value("Property Setter", setter.name, "value", json.dumps(order), update_modified=False)

    # This column was created interactively in Customize Form and is no
    # longer needed after making Leave Approval full width.
    if frappe.db.exists("Custom Field", "Employee-custom_column_break_arrzi"):
        frappe.delete_doc("Custom Field", "Employee-custom_column_break_arrzi", ignore_permissions=True)

    frappe.clear_cache(doctype="Employee")


def _merge_personal_and_contacts(order):
    """Use Personal as the single tab for contact, address and personal data."""
    required = {"contact_details", "attendance_and_leave_details", "personal_details", "profile_tab"}
    if not required.issubset(order):
        return order
    contact_start = order.index("contact_details")
    attendance_start = order.index("attendance_and_leave_details")
    personal_start = order.index("personal_details")
    profile_start = order.index("profile_tab")
    contact_fields = order[contact_start + 1:attendance_start]
    personal_fields = order[personal_start + 1:profile_start]
    moving = {"contact_details", "personal_details", *contact_fields, *personal_fields}
    merged = [fieldname for fieldname in order if fieldname not in moving]
    anchor = merged.index("attendance_and_leave_details")
    merged[anchor:anchor] = ["personal_details", *contact_fields, *personal_fields]
    return merged
