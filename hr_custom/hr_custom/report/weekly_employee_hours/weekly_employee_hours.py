from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate

from hr_custom.services.work_schedule import get_employee_schedule, get_holidays


def execute(filters=None):
    filters = frappe._dict(filters or {})
    start = getdate(filters.week_start)
    end = start + timedelta(days=6)
    employees = _employees(filters)
    logs = _logs([row.name for row in employees], start, end)
    data = []
    weekly = defaultdict(lambda: {"scheduled": 0.0, "actual": 0.0})

    for employee in employees:
        try:
            schedule, source = get_employee_schedule(employee.name)
        except frappe.ValidationError:
            schedule, source = {}, _("Not configured")
        holidays = get_holidays(employee.name, start, end)
        for offset in range(7):
            day = start + timedelta(days=offset)
            day_logs = logs.get((employee.name, day), [])
            scheduled = 0 if day in holidays else flt(schedule.get(day.strftime("%A"), 0), 2)
            actual, incomplete = _worked_hours(day_logs)
            variance = flt(actual - scheduled, 2)
            weekly[employee.name]["scheduled"] += scheduled
            weekly[employee.name]["actual"] += actual
            if filters.show_only_exceptions and not incomplete and abs(variance) < 0.01:
                continue
            data.append({
                "employee": employee.name, "employee_name": employee.employee_name,
                "employee_name_ar": employee.custom_employee_name_ar, "department": employee.department,
                "work_date": day, "day_of_week": _(day.strftime("%A")), "schedule": source,
                "scheduled_hours": scheduled, "actual_hours": actual, "variance_hours": variance,
                "first_in": day_logs[0].time if day_logs else None,
                "last_out": day_logs[-1].time if day_logs and day_logs[-1].log_type == "OUT" else None,
                "log_count": len(day_logs), "incomplete_logs": incomplete,
                "checkin_logs": " | ".join(f"{row.log_type or '?'} {get_datetime(row.time).strftime('%H:%M')}" for row in day_logs),
            })

    message = _("Week: {0} to {1}. Actual hours are calculated from matched IN → OUT Employee Checkin pairs.").format(start, end)
    chart = _chart(employees, weekly)
    return _columns(), data, message, chart


def _employees(filters):
    conditions = {"status": "Active"}
    for field in ("employee", "company", "department"):
        if filters.get(field):
            conditions["name" if field == "employee" else field] = filters[field]
    return frappe.get_all("Employee", filters=conditions, fields=["name", "employee_name", "custom_employee_name_ar", "department"], order_by="employee_name")


def _logs(employees, start, end):
    grouped = defaultdict(list)
    if not employees:
        return grouped
    rows = frappe.get_all("Employee Checkin", filters={"employee": ["in", employees], "time": ["between", [start, end + timedelta(days=1)]]}, fields=["name", "employee", "employee_name", "time", "log_type"], order_by="employee asc, time asc")
    for row in rows:
        if getdate(row.time) <= end:
            grouped[(row.employee, getdate(row.time))].append(row)
    return grouped


def _worked_hours(logs):
    total, open_in, incomplete = 0.0, None, False
    for log in logs:
        if log.log_type == "IN":
            if open_in is not None:
                incomplete = True
            open_in = get_datetime(log.time)
        elif log.log_type == "OUT":
            if open_in is None:
                incomplete = True
            else:
                total += max((get_datetime(log.time) - open_in).total_seconds(), 0) / 3600
                open_in = None
        else:
            incomplete = True
    return flt(total, 2), int(incomplete or open_in is not None)


def _columns():
    specs = [
        ("employee", "Employee", "Link", "Employee", 110), ("employee_name", "Employee Name (English)", "Data", None, 170),
        ("employee_name_ar", "Employee Name (Arabic)", "Data", None, 170), ("department", "Department", "Link", "Department", 130),
        ("work_date", "Date", "Date", None, 95), ("day_of_week", "Day", "Data", None, 85), ("schedule", "Schedule Source", "Data", None, 150),
        ("scheduled_hours", "Scheduled Hours", "Float", None, 105), ("actual_hours", "Actual Hours", "Float", None, 95),
        ("variance_hours", "Variance", "Float", None, 85), ("first_in", "First IN", "Datetime", None, 140),
        ("last_out", "Last OUT", "Datetime", None, 140), ("log_count", "Logs", "Int", None, 55),
        ("incomplete_logs", "Incomplete", "Check", None, 75), ("checkin_logs", "Check-in / Out Logs", "Small Text", None, 240),
    ]
    return [{"fieldname": field, "label": _(label), "fieldtype": fieldtype, "options": options, "width": width} for field, label, fieldtype, options, width in specs]


def _chart(employees, weekly):
    labels = [employee.employee_name for employee in employees]
    return {"data": {"labels": labels, "datasets": [
        {"name": _("Scheduled"), "values": [flt(weekly[e.name]["scheduled"], 2) for e in employees]},
        {"name": _("Actual"), "values": [flt(weekly[e.name]["actual"], 2) for e in employees]},
    ]}, "type": "bar", "colors": ["#7c3aed", "#10b981"]}
