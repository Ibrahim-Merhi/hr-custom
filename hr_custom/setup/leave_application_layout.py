import json

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


PREFERRED_FIELD_ORDER = [
    "naming_series",
    "employee",
    "employee_name",
    "column_break_4",
    "leave_type",
    "company",
    "department",
    "section_break_5",
    "from_date",
    "half_day",
    "half_day_date",
    "total_leave_days",
    "column_break1",
    "to_date",
    "description",
    "custom_hourly_leave_section",
    "custom_leave_unit",
    "custom_leave_duration",
    "custom_partial_hours",
    "custom_hourly_totals_column",
    "custom_scheduled_hours",
    "custom_leave_hours",
    "custom_hour_balance_before",
    "custom_hour_balance_after",
    "custom_leave_hour_details",
    "custom_approval_workflow_section",
    "custom_approval_stage",
    "custom_current_approver",
    "custom_approval_steps",
    "custom_hr_override_note",
    "custom_final_approved_by",
    "custom_final_approval_date",
    "leave_balance",
    "custom_legacy_leave_section",
    "custom_return_to_work_date",
    "custom_legacy_voucher_number",
    "custom_legacy_balance_deducted",
    "custom_legacy_period_starting",
    "custom_is_migrated_record",
    "section_break_7",
    "leave_approver",
    "leave_approver_name",
    "follow_via_email",
    "column_break_18",
    "posting_date",
    "status",
    "sb_other_details",
    "salary_slip",
    "color",
    "column_break_17",
    "letter_head",
    "amended_from",
]


def _set_property(fieldname, property_name, value, property_type):
    name = f"Leave Application-{fieldname}-{property_name}"
    if frappe.db.exists("Property Setter", name):
        frappe.db.set_value("Property Setter", name, "value", str(value), update_modified=False)
        return
    make_property_setter(
        "Leave Application", fieldname, property_name, value, property_type
    )


def apply_leave_application_layout():
    """Keep the operational leave form compact while preserving legacy data."""
    current = [field.fieldname for field in frappe.get_meta("Leave Application").fields]
    order = [fieldname for fieldname in PREFERRED_FIELD_ORDER if fieldname in current]
    order.extend(fieldname for fieldname in current if fieldname not in order)

    setter = frappe.db.get_value(
        "Property Setter",
        {"doc_type": "Leave Application", "property": "field_order"},
        "name",
    )
    value = json.dumps(order)
    if setter:
        frappe.db.set_value("Property Setter", setter, "value", value, update_modified=False)
    else:
        make_property_setter(
            "Leave Application", None, "field_order", value, "Data", for_doctype=True
        )

    _set_property("sb_other_details", "hidden", 1, "Check")
    _set_property("company", "read_only", 1, "Check")
    _set_property("leave_approver", "read_only", 1, "Check")
    frappe.clear_cache(doctype="Leave Application")
