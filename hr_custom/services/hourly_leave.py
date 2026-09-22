from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate

from hr_custom.services.work_schedule import (
    get_employee_schedule,
    get_holidays,
    get_leave_unit,
    validate_unit_eligibility,
)

FULL_DURATION = "Full Scheduled Hours"
PARTIAL_DURATION = "Partial Hours"


def calculate_hourly_leave(
    employee: str,
    leave_type: str,
    from_date,
    to_date,
    duration: str = FULL_DURATION,
    partial_hours=None,
) -> dict:
    if not all((employee, leave_type, from_date, to_date)):
        frappe.throw(_("Employee, Leave Type, From Date and To Date are required."))
    validate_unit_eligibility(employee, leave_type)
    if get_leave_unit(leave_type) != "Hours":
        frappe.throw(_("Leave Type {0} is not measured in Hours.").format(frappe.bold(leave_type)))

    start, end = getdate(from_date), getdate(to_date)
    if end < start:
        frappe.throw(_("To Date cannot be before From Date."))
    duration = duration or FULL_DURATION
    if duration not in (FULL_DURATION, PARTIAL_DURATION):
        frappe.throw(_("Select a valid hourly leave duration."))
    if duration == PARTIAL_DURATION and start != end:
        frappe.throw(_("Partial Hours leave is limited to a single date."))

    schedule, source = get_employee_schedule(employee, start)
    holidays = get_holidays(employee, start, end)
    details = []
    current = start
    while current <= end:
        day = current.strftime("%A")
        scheduled = flt(schedule.get(day, 0), 2)
        holiday = current in holidays
        non_working = scheduled <= 0
        leave_hours = 0 if holiday or non_working else scheduled
        remarks = _("Holiday") if holiday else (_("Non-working day") if non_working else "")
        details.append(
            {
                "leave_date": current,
                "day_of_week": day,
                "scheduled_hours": scheduled,
                "leave_hours": leave_hours,
                "is_holiday": cint(holiday),
                "is_non_working_day": cint(non_working),
                "schedule_source": source,
                "remarks": remarks,
            }
        )
        current = getdate(add_days(current, 1))

    if duration == PARTIAL_DURATION:
        requested = flt(partial_hours, 2)
        available = details[0]["leave_hours"]
        if requested <= 0:
            frappe.throw(_("Requested Hours must be greater than zero."))
        if available <= 0:
            frappe.throw(_("Partial hourly leave cannot be requested on a holiday or non-working day."))
        if requested > available:
            frappe.throw(
                _("Requested Hours cannot exceed the scheduled {0} hours.").format(frappe.bold(available))
            )
        details[0]["leave_hours"] = requested
        details[0]["remarks"] = _("Partial hours")

    total_scheduled = flt(sum(row["scheduled_hours"] for row in details), 2)
    total_leave = flt(sum(row["leave_hours"] for row in details), 2)
    if total_leave <= 0:
        frappe.throw(_("The selected period contains no scheduled working hours eligible for leave."))
    return {
        "leave_unit": "Hours",
        "schedule_source": source,
        "total_scheduled_hours": total_scheduled,
        "total_leave_hours": total_leave,
        "details": details,
    }


def get_hour_leave_balance(employee: str, leave_type: str, date, exclude_application=None) -> dict:
    if get_leave_unit(leave_type) != "Hours":
        frappe.throw(_("Leave Type {0} is not measured in Hours.").format(frappe.bold(leave_type)))
    date = getdate(date)
    allocations = frappe.get_all(
        "Leave Allocation",
        filters={
            "employee": employee,
            "leave_type": leave_type,
            "docstatus": 1,
            "expired": 0,
            "from_date": ("<=", date),
            "to_date": (">=", date),
        },
        fields=["name", "from_date", "to_date", "total_leaves_allocated"],
    )
    allocated = flt(sum(flt(row.total_leaves_allocated) for row in allocations), 2)
    if allocations:
        period_start = min(getdate(row.from_date) for row in allocations)
        period_end = max(getdate(row.to_date) for row in allocations)
    else:
        period_start = period_end = date

    filters = {
        "employee": employee,
        "leave_type": leave_type,
        "docstatus": 1,
        "status": "Approved",
        "custom_leave_unit": "Hours",
        "to_date": (">=", period_start),
        "from_date": ("<=", period_end),
    }
    if exclude_application:
        filters["name"] = ("!=", exclude_application)
    applications = frappe.get_all("Leave Application", filters=filters, fields=["custom_leave_hours"])
    used = flt(sum(flt(row.custom_leave_hours) for row in applications), 2)
    return {
        "allocated_hours": allocated,
        "used_hours": used,
        "remaining_hours": flt(allocated - used, 2),
        "allocation_from": period_start if allocations else None,
        "allocation_to": period_end if allocations else None,
    }


def apply_calculation(doc) -> dict:
    unit = get_leave_unit(doc.leave_type)
    doc.custom_leave_unit = unit
    if unit != "Hours":
        doc.custom_leave_hour_details = []
        for field in ("custom_scheduled_hours", "custom_leave_hours", "custom_hour_balance_before", "custom_hour_balance_after"):
            doc.set(field, 0)
        return {"leave_unit": unit}

    result = calculate_hourly_leave(
        doc.employee,
        doc.leave_type,
        doc.from_date,
        doc.to_date,
        doc.custom_leave_duration or FULL_DURATION,
        doc.custom_partial_hours,
    )
    doc.set("custom_leave_hour_details", [])
    for detail in result["details"]:
        doc.append("custom_leave_hour_details", detail)
    doc.custom_scheduled_hours = result["total_scheduled_hours"]
    doc.custom_leave_hours = result["total_leave_hours"]
    balance = get_hour_leave_balance(doc.employee, doc.leave_type, doc.from_date, doc.name)
    doc.custom_hour_balance_before = balance["remaining_hours"]
    doc.custom_hour_balance_after = flt(balance["remaining_hours"] - doc.custom_leave_hours, 2)
    result["balance"] = balance
    result["balance_after_leave"] = doc.custom_hour_balance_after
    return result


def validate_hour_balance(doc):
    if get_leave_unit(doc.leave_type) != "Hours" or doc.status == "Rejected":
        return
    if frappe.db.get_value("Leave Type", doc.leave_type, "is_lwp"):
        return
    allow_negative = frappe.db.get_value("Leave Type", doc.leave_type, "allow_negative")
    available = flt(doc.custom_hour_balance_before, 2)
    requested = flt(doc.custom_leave_hours, 2)
    if not allow_negative and requested > available:
        frappe.throw(
            _("Insufficient {0} balance. Available: {1} hours. Requested: {2} hours.").format(
                frappe.bold(doc.leave_type), available, requested
            ),
            title=_("Insufficient Balance"),
        )
