import json

import frappe

PREFIX = "hr_custom_"
GROUPS = [
    ("Employee Communications", [
        ("HR Announcement", "DocType", "HR Announcement", "Green"),
    ]),
    ("Work Schedules & Hourly Leave", [
        ("Weekly Work Schedule", "DocType", "Weekly Work Schedule", "Blue"),
        ("Weekly Employee Hours", "Report", "Weekly Employee Hours", "Blue"),
        ("Hourly Leave Balance", "Report", "Hourly Leave Balance", "Blue"),
    ]),
    ("Leave Management", [
        ("Yearly Leave Allocation", "DocType", "Yearly Leave Allocation", "Green"),
        ("Yearly Leave Allocation Summary", "Report", "Yearly Leave Allocation Summary", "Blue"),
        ("Leave Allocation", "DocType", "Leave Allocation", "Grey"),
        ("Leave Application", "DocType", "Leave Application", "Grey"),
    ]),
    ("Attendance Operations", [
        ("GPS Attendance", "URL", "/attendance", "Green"),
        ("Attendance Correction Request", "DocType", "Attendance Correction Request", "Orange"),
        ("Attendance Exception", "DocType", "Attendance Exception", "Red"),
        ("Daily Attendance Overview", "Report", "Daily Attendance Overview", "Blue"),
        ("Mobile Checkin Audit", "Report", "Mobile Checkin Audit", "Grey"),
        ("Attendance Exceptions", "Report", "Attendance Exceptions", "Grey"),
        ("Abnormal Attendance Records", "Report", "Abnormal Attendance Records", "Orange"),
    ]),
    ("Attendance Configuration", [
        ("HR Mobile Attendance Settings", "DocType", "HR Mobile Attendance Settings", "Grey"),
        ("Employee Attendance Device", "DocType", "Employee Attendance Device", "Grey"),
    ]),
    ("Portal Access", [
        ("Employee Portal Credential", "DocType", "Employee Portal Credential", "Green"),
    ]),
]
LABELS = {item[0] for _, items in GROUPS for item in items} | {"Mobile Attendance", "HR Attendance Dashboard", "Daily Attendance Overview"}


def ensure_hr_workspace_section():
    if not frappe.db.exists("Workspace", "HR"):
        return
    doc = frappe.get_doc("Workspace", "HR")
    content = [item for item in json.loads(doc.content or "[]") if not item.get("id", "").startswith(PREFIX)]
    shortcut_number = 0
    for group_number, (title, items) in enumerate(GROUPS):
        content.append({"id": f"{PREFIX}header_{group_number}", "type": "header", "data": {"text": f'<span class="h4"><b>{title}</b></span>', "col": 12}})
        for label, _, _, _ in items:
            content.append({"id": f"{PREFIX}shortcut_{shortcut_number}", "type": "shortcut", "data": {"shortcut_name": label, "col": 4}})
            shortcut_number += 1
        content.append({"id": f"{PREFIX}spacer_{group_number}", "type": "spacer", "data": {"col": 12}})
    doc.content = json.dumps(content, separators=(",", ":"))
    doc.set("shortcuts", [row.as_dict() for row in doc.shortcuts if row.label not in LABELS])
    for _, items in GROUPS:
        for label, kind, target, color in items:
            row = {"type": kind, "label": label, "color": color}
            if kind == "URL":
                row["url"] = target
            else:
                row["link_to"] = target
            if kind == "DocType":
                row["doc_view"] = "List"
            doc.append("shortcuts", row)
    _save(doc)


def remove_hr_workspace_section():
    if not frappe.db.exists("Workspace", "HR"):
        return
    doc = frappe.get_doc("Workspace", "HR")
    doc.content = json.dumps([item for item in json.loads(doc.content or "[]") if not item.get("id", "").startswith(PREFIX)], separators=(",", ":"))
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
