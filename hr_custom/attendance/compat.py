import frappe


def has_field(doctype, fieldname):
    return bool(frappe.get_meta(doctype).has_field(fieldname))


def supported_values(doctype, values):
    return {key: value for key, value in values.items() if has_field(doctype, key)}

