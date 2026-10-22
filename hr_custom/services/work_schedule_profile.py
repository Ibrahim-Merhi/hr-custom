from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from hr_custom.services.work_schedule import DAYS


def _check_access(employee, write=False):
    if not employee or not frappe.db.exists("Employee", employee):
        frappe.throw(_("Select a valid employee."))
    if frappe.session.user == "Administrator":
        return
    permission = "write" if write else "read"
    if not frappe.has_permission("Employee", permission, employee):
        frappe.throw(_("You do not have permission to manage this employee's work schedule."), frappe.PermissionError)


def _rows(employee):
    return frappe.get_all(
        "Employee Working Hours",
        filters={"parent": employee, "parenttype": "Employee", "parentfield": "custom_weekly_working_hours"},
        fields=["day_of_week", "working_hours", "from_time", "to_time", "enabled", "sequence"],
        order_by="sequence asc, idx asc",
    )


@frappe.whitelist()
def get_profile(employee):
    _check_access(employee)
    rows = _rows(employee)
    revisions = frappe.get_all(
        "Employee Work Schedule Revision", filters={"employee": employee},
        fields=["name", "revision_number", "effective_from", "effective_to", "action_date", "changed_by", "total_weekly_hours", "change_summary"],
        order_by="revision_number desc", limit_page_length=0,
    )
    for revision in revisions:
        revision.schedule = frappe.get_all(
            "Employee Work Schedule Revision Day", filters={"parent": revision.name},
            fields=["day_of_week", "working_hours", "from_time", "to_time", "enabled"], order_by="idx asc",
        )
    return {"rows": rows, "revisions": revisions, "revision_count": len(revisions)}


def _normalized(rows):
    result = []
    seen = set()
    for index, row in enumerate(rows or [], 1):
        day = row.get("day_of_week")
        if day not in DAYS or day in seen:
            frappe.throw(_("Each selected day must appear only once."))
        seen.add(day)
        hours = flt(row.get("working_hours"), 2)
        if hours < 0 or hours > 24:
            frappe.throw(_("Working hours for {0} must be between 0 and 24.").format(_(day)))
        result.append({
            "day_of_week": day, "working_hours": hours,
            "from_time": row.get("from_time") or None, "to_time": row.get("to_time") or None,
            "enabled": 1 if row.get("enabled", 1) else 0, "sequence": DAYS.index(day) + 1,
        })
    return sorted(result, key=lambda row: row["sequence"])


def _signature(rows):
    return [(r.get("day_of_week"), flt(r.get("working_hours"), 2), str(r.get("from_time") or ""), str(r.get("to_time") or ""), int(r.get("enabled", 1))) for r in rows]


def _change_summary(before, after):
    old = {row.get("day_of_week"): row for row in before}
    new = {row.get("day_of_week"): row for row in after}
    changes = []
    for day in DAYS:
        previous, current = old.get(day), new.get(day)
        if not previous and current:
            changes.append(_("{0} added: {1} hours, {2} to {3}").format(_(day), current["working_hours"], current.get("from_time") or "—", current.get("to_time") or "—"))
        elif previous and not current:
            changes.append(_("{0} removed").format(_(day)))
        elif previous and current and _signature([previous]) != _signature([current]):
            changes.append(_("{0}: {1} hours {2}–{3} changed to {4} hours {5}–{6}").format(
                _(day), flt(previous.get("working_hours"), 2), previous.get("from_time") or "—", previous.get("to_time") or "—",
                current["working_hours"], current.get("from_time") or "—", current.get("to_time") or "—",
            ))
    return "; ".join(changes)


@frappe.whitelist(methods=["POST"])
def save_profile(payload):
    data = frappe.parse_json(payload) if isinstance(payload, str) else payload
    employee = data.get("employee")
    _check_access(employee, write=True)
    frappe.db.sql("select name from `tabEmployee` where name = %s for update", employee)
    rows = _normalized(data.get("rows"))
    if not rows:
        frappe.throw(_("Add at least one working day."))
    current = _rows(employee)
    if _signature(rows) == _signature(current):
        frappe.throw(_("The work schedule has no changes."))

    effective_from = getdate(data.get("effective_from") or nowdate())
    action_date = getdate(data.get("action_date") or nowdate())
    previous = frappe.get_all("Employee Work Schedule Revision", filters={"employee": employee}, fields=["name", "revision_number", "effective_from"], order_by="revision_number desc", limit=1)
    if previous and effective_from < getdate(previous[0].effective_from):
        frappe.throw(_("Effective From cannot be before the current schedule's effective date."))

    doc = frappe.get_doc("Employee", employee)
    doc.custom_use_custom_work_schedule = 1
    doc.set("custom_weekly_working_hours", [])
    for row in rows:
        doc.append("custom_weekly_working_hours", row)
    doc.save()

    if previous:
        previous_end = (
            add_days(effective_from, -1)
            if effective_from > getdate(previous[0].effective_from)
            else effective_from
        )
        frappe.db.set_value(
            "Employee Work Schedule Revision",
            previous[0].name,
            "effective_to",
            previous_end,
            update_modified=False,
        )
    automatic_summary = _change_summary(current, rows)
    reason = (data.get("change_summary") or "").strip()
    revision = frappe.get_doc({
        "doctype": "Employee Work Schedule Revision", "employee": employee,
        "employee_name": doc.employee_name, "revision_number": (previous[0].revision_number if previous else 0) + 1,
        "effective_from": effective_from, "action_date": action_date, "changed_by": frappe.session.user,
        "total_weekly_hours": sum(row["working_hours"] for row in rows if row["enabled"]),
        "change_summary": f"{reason}: {automatic_summary}" if reason else automatic_summary,
    })
    for row in rows:
        revision.append("schedule", {key: row.get(key) for key in ("day_of_week", "working_hours", "from_time", "to_time", "enabled")})
    revision.insert(ignore_permissions=True)
    return get_profile(employee)
