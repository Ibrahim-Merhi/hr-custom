from __future__ import annotations

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate, now_datetime
from hrms.hr.utils import get_holiday_dates_for_employee

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MAX_DAILY_HOURS = 24


def get_employee_leave_mode(employee: str) -> str:
    values = frappe.db.get_value(
        "Employee",
        employee,
        ["employment_type", "custom_leave_calculation_mode_override"],
        as_dict=True,
    )
    if values and values.custom_leave_calculation_mode_override:
        return values.custom_leave_calculation_mode_override
    employment_type = values.employment_type if values else None
    if not employment_type:
        return "Days"
    return frappe.db.get_value("Employment Type", employment_type, "custom_leave_calculation_mode") or "Days"


def get_leave_unit(leave_type: str) -> str:
    return frappe.db.get_value("Leave Type", leave_type, "custom_leave_unit") or "Days"


def validate_unit_eligibility(employee: str, leave_type: str) -> tuple[str, str]:
    mode = get_employee_leave_mode(employee)
    unit = get_leave_unit(leave_type)
    if mode != "Both" and mode != unit:
        frappe.throw(
            _("Employment Type leave mode {0} does not allow Leave Type {1}, which is measured in {2}.").format(
                frappe.bold(mode), frappe.bold(leave_type), frappe.bold(unit)
            )
        )
    return mode, unit


def get_employee_schedule(employee: str, date=None) -> tuple[dict[str, float], str]:
    values = frappe.db.get_value(
        "Employee", employee, ["employment_type", "custom_use_custom_work_schedule", "custom_weekly_work_schedule"], as_dict=True
    )
    if not values:
        frappe.throw(_("Employee {0} does not exist.").format(frappe.bold(employee)))

    if values.custom_use_custom_work_schedule:
        historical = _revision_schedule(employee, date)
        if historical:
            return historical, "Employee Schedule History"
        rows = _schedule_rows("Employee", employee, "custom_weekly_working_hours")
        if rows:
            return rows, "Employee"

    if values.custom_weekly_work_schedule:
        rows = _master_schedule_rows(values.custom_weekly_work_schedule)
        if rows:
            return rows, "Weekly Work Schedule"

    if values.employment_type:
        master = frappe.db.get_value("Employment Type", values.employment_type, "custom_weekly_work_schedule")
        if master:
            rows = _master_schedule_rows(master)
            if rows:
                return rows, "Employment Type Weekly Work Schedule"
        rows = _schedule_rows("Employment Type", values.employment_type, "custom_weekly_working_hours")
        if rows:
            return rows, "Employment Type"

    frappe.throw(_("No working-hours schedule is configured for this employee or their Employment Type."))


def _master_schedule_rows(schedule: str) -> dict[str, float]:
    if not frappe.db.get_value("Weekly Work Schedule", schedule, "enabled"):
        frappe.throw(_("Weekly Work Schedule {0} is disabled.").format(frappe.bold(schedule)))
    rows = frappe.get_all(
        "Weekly Work Schedule Day",
        filters={"parenttype": "Weekly Work Schedule", "parent": schedule, "parentfield": "working_hours", "enabled": 1},
        fields=["day_of_week", "working_hours"],
        order_by="sequence asc, idx asc",
    )
    return {row.day_of_week: flt(row.working_hours, 2) for row in rows}


def _schedule_rows(parenttype: str, parent: str, parentfield: str) -> dict[str, float]:
    childtype = "Employee Working Hours" if parenttype == "Employee" else "Employment Type Working Hours"
    rows = frappe.get_all(
        childtype,
        filters={"parenttype": parenttype, "parent": parent, "parentfield": parentfield, "enabled": 1},
        fields=["day_of_week", "working_hours"],
        order_by="sequence asc, idx asc",
    )
    return {row.day_of_week: flt(row.working_hours, 2) for row in rows}


def get_scheduled_hours(employee: str, date, schedule=None) -> tuple[float, str]:
    if schedule is None:
        schedule, source = get_employee_schedule(employee, date)
    elif isinstance(schedule, tuple):
        schedule, source = schedule
    else:
        source = "Provided"
    return flt(schedule.get(getdate(date).strftime("%A"), 0), 2), source


def get_scheduled_period(employee: str, date) -> dict:
    """Return the selected daily schedule, including its optional time window."""
    values = frappe.db.get_value(
        "Employee", employee,
        ["employment_type", "custom_use_custom_work_schedule", "custom_weekly_work_schedule"],
        as_dict=True,
    )
    if not values:
        frappe.throw(_("Employee {0} does not exist.").format(frappe.bold(employee)))

    day = getdate(date).strftime("%A")
    candidates = []
    if values.custom_use_custom_work_schedule:
        historical = _revision_schedule(employee, date, include_period=True)
        if historical:
            return historical
        candidates.append(("Employee Working Hours", "Employee", employee, "custom_weekly_working_hours", "Employee"))
    if values.custom_weekly_work_schedule:
        candidates.append(("Weekly Work Schedule Day", "Weekly Work Schedule", values.custom_weekly_work_schedule, "working_hours", "Weekly Work Schedule"))
    if values.employment_type:
        master = frappe.db.get_value("Employment Type", values.employment_type, "custom_weekly_work_schedule")
        if master:
            candidates.append(("Weekly Work Schedule Day", "Weekly Work Schedule", master, "working_hours", "Employment Type Weekly Work Schedule"))
        candidates.append(("Employment Type Working Hours", "Employment Type", values.employment_type, "custom_weekly_working_hours", "Employment Type"))

    for childtype, parenttype, parent, parentfield, source in candidates:
        row = frappe.get_all(
            childtype,
            filters={"parenttype": parenttype, "parent": parent, "parentfield": parentfield, "day_of_week": day, "enabled": 1},
            fields=["working_hours", "from_time", "to_time"],
            limit=1,
        )
        if row:
            return {
                "working_hours": flt(row[0].working_hours, 2),
                "from_time": row[0].from_time,
                "to_time": row[0].to_time,
                "source": source,
            }
    return {"working_hours": 0, "from_time": None, "to_time": None, "source": None}


def get_unpunched_attendance_status(employee: str, attendance_date, current_datetime=None) -> str:
    """Classify a day with no IN punch without declaring absence too early."""
    attendance_date = getdate(attendance_date)
    period = get_scheduled_period(employee, attendance_date)
    if flt(period.get("working_hours"), 2) <= 0 or get_holiday_status(employee, attendance_date):
        return "Non-working"

    current = get_datetime(current_datetime or now_datetime())
    if attendance_date < getdate(current):
        return "Absent"
    if attendance_date > getdate(current):
        return "Scheduled"

    # Without a configured start time there is no defensible point during the
    # current day at which the employee can be called absent.
    if not period.get("from_time"):
        return "Scheduled"
    scheduled_start = datetime.combine(attendance_date, time.min) + _as_timedelta(period["from_time"])
    return "Absent" if current >= scheduled_start else "Scheduled"


def _revision_schedule(employee: str, date=None, include_period=False):
    """Return the employee-specific schedule effective on ``date`` when history exists."""
    if not date or not frappe.db.exists("DocType", "Employee Work Schedule Revision"):
        return None
    target = getdate(date)
    revisions = frappe.get_all(
        "Employee Work Schedule Revision",
        filters={
            "employee": employee,
            "effective_from": ["<=", target],
        },
        fields=["name", "effective_to"],
        order_by="effective_from desc, revision_number desc",
        limit_page_length=0,
    )
    revision = next(
        (item for item in revisions if not item.effective_to or getdate(item.effective_to) >= target),
        None,
    )
    if not revision:
        return None
    rows = frappe.get_all(
        "Employee Work Schedule Revision Day",
        filters={"parent": revision.name, "parentfield": "schedule", "enabled": 1},
        fields=["day_of_week", "working_hours", "from_time", "to_time"],
        order_by="idx asc",
    )
    if include_period:
        day = target.strftime("%A")
        row = next((item for item in rows if item.day_of_week == day), None)
        return {
            "working_hours": flt(row.working_hours, 2) if row else 0,
            "from_time": row.from_time if row else None,
            "to_time": row.to_time if row else None,
            "source": "Employee Schedule History",
        }
    return {row.day_of_week: flt(row.working_hours, 2) for row in rows}


def get_holiday_status(employee: str, date, holiday_dates=None) -> bool:
    if holiday_dates is None:
        holiday_dates = {getdate(value) for value in get_holiday_dates_for_employee(employee, date, date)}
    return getdate(date) in holiday_dates


def get_holidays(employee: str, from_date, to_date) -> set:
    return {
        getdate(value)
        for value in get_holiday_dates_for_employee(employee, getdate(from_date), getdate(to_date))
    }


def validate_schedule_document(doc, method=None):
    if doc.doctype == "Employee" and not doc.get("custom_use_custom_work_schedule"):
        return
    fieldname = "working_hours" if doc.doctype == "Weekly Work Schedule" else "custom_weekly_working_hours"
    rows = doc.get(fieldname) or []
    seen = set()
    for index, row in enumerate(rows, 1):
        day = row.day_of_week
        if day not in DAYS:
            frappe.throw(_("Row {0}: select a valid day of the week.").format(index))
        if day in seen:
            frappe.throw(_("{0} appears more than once in the weekly working-hours schedule.").format(_(day)))
        seen.add(day)
        hours = flt(row.working_hours)
        if hours < 0 or hours > MAX_DAILY_HOURS:
            frappe.throw(_("Working hours for {0} must be between 0 and 24.").format(_(day)))
        if bool(row.from_time) != bool(row.to_time):
            frappe.throw(_("Provide both From Time and To Time for {0}, or leave both empty.").format(_(day)))
        if row.from_time and row.to_time:
            start, end = _as_timedelta(row.from_time), _as_timedelta(row.to_time)
            if end <= start:
                frappe.throw(_("To Time must be after From Time for {0}.").format(_(day)))
        row.sequence = DAYS.index(day) + 1
    if doc.doctype == "Weekly Work Schedule":
        doc.total_weekly_hours = flt(sum(flt(row.working_hours) for row in rows if row.enabled), 2)


def _as_timedelta(value) -> timedelta:
    if isinstance(value, timedelta):
        return value
    parts = str(value).split(":")
    return timedelta(hours=int(parts[0]), minutes=int(parts[1]), seconds=float(parts[2] or 0))
