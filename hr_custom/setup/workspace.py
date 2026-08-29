import json
import frappe

PREFIX = "hr_custom_"
LABELS = {"Mobile Attendance", "Attendance Correction Request", "Attendance Exception"}


def ensure_hr_workspace_section():
    if not frappe.db.exists("Workspace", "HR"):
        return
    doc = frappe.get_doc("Workspace", "HR")
    content = [x for x in json.loads(doc.content or "[]") if not x.get("id", "").startswith(PREFIX)]
    content.extend([
        {"id": "hr_custom_header", "type": "header", "data": {"text": '<span class="h4"><b>Custom HRMS</b></span>', "col": 12}},
        {"id": "hr_custom_mobile", "type": "shortcut", "data": {"shortcut_name": "Mobile Attendance", "col": 4}},
        {"id": "hr_custom_correction", "type": "shortcut", "data": {"shortcut_name": "Attendance Correction Request", "col": 4}},
        {"id": "hr_custom_exception", "type": "shortcut", "data": {"shortcut_name": "Attendance Exception", "col": 4}},
    ])
    doc.content = json.dumps(content, separators=(",", ":"))
    doc.set("shortcuts", [row.as_dict() for row in doc.shortcuts if row.label not in LABELS])
    doc.append("shortcuts", {"type": "URL", "label": "Mobile Attendance", "url": "/attendance", "color": "Green"})
    doc.append("shortcuts", {"type": "DocType", "label": "Attendance Correction Request", "link_to": "Attendance Correction Request", "doc_view": "List", "color": "Blue"})
    doc.append("shortcuts", {"type": "DocType", "label": "Attendance Exception", "link_to": "Attendance Exception", "doc_view": "List", "color": "Orange"})
    _save(doc)


def remove_hr_workspace_section():
    if not frappe.db.exists("Workspace", "HR"):
        return
    doc = frappe.get_doc("Workspace", "HR")
    doc.content = json.dumps([x for x in json.loads(doc.content or "[]") if not x.get("id", "").startswith(PREFIX)], separators=(",", ":"))
    doc.set("shortcuts", [row.as_dict() for row in doc.shortcuts if row.label not in LABELS])
    _save(doc)


def _save(doc):
    for index, row in enumerate(doc.shortcuts, 1):
        row.idx = index
    doc.flags.ignore_permissions = True
    developer_mode = frappe.conf.developer_mode
    try:
        frappe.conf.developer_mode = 0
        doc.save()
    finally:
        frappe.conf.developer_mode = developer_mode
    frappe.clear_cache(doctype="Workspace")
