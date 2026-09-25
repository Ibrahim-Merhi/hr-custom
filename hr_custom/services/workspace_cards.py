from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.utils import getdate, nowdate


COMPANY = "Itihad"


def _result(value, route, route_options=None):
    return {"value": value, "route": route, "route_options": route_options or {}}


def _active_employee_names(today=None):
    today = getdate(today or nowdate())
    return frappe.get_all(
        "Employee",
        filters={"company": COMPANY, "status": "Active", "date_of_joining": ["<=", today]},
        pluck="name",
        limit_page_length=0,
    )


@frappe.whitelist()
def active_employees(filters=None):
    value = frappe.db.count("Employee", {"company": COMPANY, "status": "Active"})
    return _result(value, ["List", "Employee"], {"company": COMPANY, "status": "Active"})


def _present_employee_names(today=None):
    today = getdate(today or nowdate())
    employees = _active_employee_names(today)
    if not employees:
        return set()
    start = f"{today} 00:00:00"
    end = f"{today + timedelta(days=1)} 00:00:00"
    return set(frappe.get_all(
        "Employee Checkin",
        filters=[["employee", "in", employees], ["time", ">=", start], ["time", "<", end]],
        pluck="employee",
        distinct=True,
        limit_page_length=0,
    ))


@frappe.whitelist()
def present_today(filters=None):
    return _result(len(_present_employee_names()), ["query-report", "Daily Attendance Overview"], {"period_type": "Day", "date": nowdate(), "attendance_status": "Present", "company": COMPANY})


@frappe.whitelist()
def absent_today(filters=None):
    active = set(_active_employee_names())
    value = len(active - _present_employee_names())
    return _result(value, ["query-report", "Daily Attendance Overview"], {"period_type": "Day", "date": nowdate(), "attendance_status": "Absent", "company": COMPANY})


@frappe.whitelist()
def on_leave_today(filters=None):
    today = nowdate()
    value = frappe.db.count("Leave Application", {
        "company": COMPANY, "status": "Approved", "docstatus": 1,
        "from_date": ["<=", today], "to_date": [">=", today],
    })
    return _result(value, ["List", "Leave Application"], {"company": COMPANY, "status": "Approved", "from_date": ["<=", today], "to_date": [">=", today]})
