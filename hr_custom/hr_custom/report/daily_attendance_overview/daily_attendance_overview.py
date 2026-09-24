from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_first_day, get_last_day, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	start, end = _date_range(filters)
	columns = _columns()
	employees = _employees(filters, start, end)
	if not employees:
		return columns, []

	branch_names = {row.branch for row in employees if row.branch}
	branch_names_ar = {row.name: row.custom_branch_name_arabic for row in frappe.get_all("Branch", filters={"name": ["in", list(branch_names)]}, fields=["name", "custom_branch_name_arabic"], limit_page_length=0)} if branch_names else {}

	logs = frappe.get_all(
		"Employee Checkin",
		filters=[["employee", "in", [row.name for row in employees]], ["time", ">=", start], ["time", "<", end + timedelta(days=1)]],
		fields=["employee", "time", "log_type"],
		order_by="employee asc, time asc",
		limit_page_length=0,
	)
	by_employee_date = defaultdict(list)
	for log in logs:
		by_employee_date[(log.employee, getdate(log.time))].append(log)

	status_filter = filters.get("attendance_status") or "All"
	rows = []
	for employee in employees:
		joined = getdate(employee.date_of_joining) if employee.date_of_joining else start
		relieved = getdate(employee.relieving_date) if employee.relieving_date else end
		date = max(start, joined)
		while date <= min(end, relieved):
			day_logs = by_employee_date.get((employee.name, date), [])
			status = "Present" if day_logs else "Absent"
			if status_filter in ("Present", "Absent") and status != status_filter:
				date += timedelta(days=1)
				continue
			ins = [row.time for row in day_logs if row.log_type == "IN"]
			outs = [row.time for row in day_logs if row.log_type == "OUT"]
			first_in, last_out = (min(ins) if ins else None), (max(outs) if outs else None)
			worked = (last_out - first_in).total_seconds() / 3600 if first_in and last_out and last_out > first_in else 0
			worked_minutes = max(0, round(worked * 60))
			worked_display = f"{worked_minutes / 60:.0f}:{worked_minutes % 60:02d}" if worked_minutes else "0:00"
			rows.append({
				"employee": employee.name,
				"employee_name": employee.employee_name,
				"employee_name_ar": employee.custom_employee_name_ar,
				"department": employee.department,
				"branch": employee.branch,
				"branch_name_ar": branch_names_ar.get(employee.branch) or employee.branch,
				"date": date,
				"day": _(date.strftime("%A")),
				"status": _(status),
				"first_in": first_in.strftime("%H:%M:%S") if first_in else None,
				"last_out": last_out.strftime("%H:%M:%S") if last_out else None,
				"working_hours": worked_display,
				"working_hours_decimal": round(worked, 2),
			})
			date += timedelta(days=1)
	return columns, rows


def _date_range(filters):
	anchor = getdate(filters.get("date") or nowdate())
	period = filters.get("period_type") or "Day"
	if period == "Week":
		return anchor - timedelta(days=anchor.weekday()), anchor - timedelta(days=anchor.weekday()) + timedelta(days=6)
	if period == "Month":
		return getdate(get_first_day(anchor)), getdate(get_last_day(anchor))
	return anchor, anchor


def _employees(filters, start, end):
	query_filters = {"status": "Active", "date_of_joining": ["<=", end]}
	for field in ("company", "branch", "department"):
		if filters.get(field):
			query_filters[field] = filters[field]
	return frappe.get_all(
		"Employee",
		filters=query_filters,
		fields=["name", "employee_name", "custom_employee_name_ar", "department", "branch", "date_of_joining", "relieving_date"],
		order_by="employee_name asc",
		limit_page_length=0,
	)


def _columns():
	return [
		{"label": _("Employee Name"), "fieldname": "employee_name", "width": 190},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 105},
		{"label": _("Day"), "fieldname": "day", "width": 100},
		{"label": _("Status"), "fieldname": "status", "width": 90},
		{"label": _("First Clock In"), "fieldname": "first_in", "fieldtype": "Time", "width": 110},
		{"label": _("Last Clock Out"), "fieldname": "last_out", "fieldtype": "Time", "width": 110},
		{"label": _("Working Hours (H:MM)"), "fieldname": "working_hours", "fieldtype": "Data", "width": 130},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 130},
	]
