import frappe
from frappe import _
from frappe.utils import cint, flt, get_last_day, getdate, nowdate


@frappe.whitelist()
def get_employee_leave_years(employee):
    _employee(employee)
    years = {getdate(nowdate()).year}
    for doctype in ("Leave Application", "Leave Allocation"):
        for row in frappe.get_list(doctype, filters={"employee": employee}, fields=["from_date", "to_date"],
                                   distinct=True, limit_page_length=0):
            if row.from_date and row.to_date:
                years.update(range(row.from_date.year, row.to_date.year + 1))
    return sorted(years, reverse=True)


@frappe.whitelist()
def get_employee_leave_history(employee, year):
    _employee(employee)
    year = cint(year)
    if not 1900 <= year <= 9999:
        frappe.throw(_("Enter a valid year."))
    start, end = getdate(f"{year}-01-01"), getdate(f"{year}-12-31")
    filters = {"employee": employee, "from_date": ["<=", end], "to_date": [">=", start]}
    requests = frappe.get_list(
        "Leave Application",
        filters=filters,
        fields=["name", "leave_type", "from_date", "to_date", "status", "docstatus",
                "total_leave_days", "custom_leave_unit", "custom_leave_hours", "half_day", "half_day_date"],
        order_by="from_date desc, name desc",
        limit_page_length=0,
    )
    from hr_custom.services.work_schedule import get_leave_unit
    from hrms.hr.doctype.leave_application.leave_application import get_number_of_leave_days

    totals = {}
    for row in frappe.get_list("Leave Allocation", filters={**filters, "docstatus": 1},
                               fields=["name", "leave_type", "from_date", "to_date", "total_leaves_allocated"],
                               order_by="from_date asc, name asc", limit_page_length=0):
        item = totals.setdefault(row.leave_type, {"allocated": 0, "used": 0, "allocations": []})
        item["allocated"] += flt(row.total_leaves_allocated)
        item["allocations"].append(row)
    for row in requests:
        if row.docstatus != 1 or row.status != "Approved":
            continue
        item = totals.setdefault(row.leave_type, {"allocated": 0, "used": 0, "allocations": []})
        hour_leave = row.custom_leave_unit == "Hours"
        used = row.custom_leave_hours if hour_leave else row.total_leave_days
        if row.from_date < start or row.to_date > end:
            first, last = max(start, row.from_date), min(end, row.to_date)
            if hour_leave:
                details = frappe.get_all("Leave Hour Detail", filters={
                    "parent": row.name, "parenttype": "Leave Application",
                    "leave_date": ["between", [first, last]],
                }, pluck="leave_hours")
                used = sum(flt(value) for value in details)
            else:
                used = get_number_of_leave_days(employee, row.leave_type, first, last,
                                                half_day=row.half_day, half_day_date=row.half_day_date)
        row.used_in_year = flt(used, 2)
        item["used"] += row.used_in_year
    return {"requests": requests, "balances": [
        {"leave_type": kind, "unit": get_leave_unit(kind), "allocated": flt(item["allocated"], 2),
         "used": flt(item["used"], 2), "remaining": flt(item["allocated"] - item["used"], 2),
         "allocations": item["allocations"]}
        for kind, item in sorted(totals.items())
    ]}


def _employee(name):
    doc = frappe.get_doc("Employee", name)
    doc.check_permission("read")
    return doc


@frappe.whitelist()
def get_employee_hr_history(employee, month=None, year=None):
    _employee(employee)
    today = getdate(nowdate())
    # Keep the Employee form fast by loading attendance for one selected month.
    month = max(1, min(cint(month) or today.month, 12))
    year = cint(year) or today.year
    period_start = getdate(f"{year:04d}-{month:02d}-01")
    period_end = get_last_day(period_start)
    allocations = frappe.get_all(
        "Leave Allocation",
        filters={"employee": employee, "docstatus": 1, "from_date": ["<=", today], "to_date": [">=", today]},
        fields=["leave_type", "total_leaves_allocated", "from_date", "to_date"],
        order_by="leave_type asc",
    )
    leave_units = {
        row.name: row.custom_leave_unit or "Days"
        for row in frappe.get_all("Leave Type", fields=["name", "custom_leave_unit"])
    }
    grouped = {}
    for allocation in allocations:
        item = grouped.setdefault(allocation.leave_type, {"leave_type": allocation.leave_type, "allocated": 0, "from_date": allocation.from_date, "to_date": allocation.to_date})
        item["allocated"] += flt(allocation.total_leaves_allocated, 2)
        item["from_date"] = min(item["from_date"], allocation.from_date)
        item["to_date"] = max(item["to_date"], allocation.to_date)

    balances = []
    for leave_type, item in grouped.items():
        unit = leave_units.get(leave_type, "Days")
        if unit == "Hours":
            from hr_custom.services.hourly_leave import get_hour_leave_balance
            remaining = flt(get_hour_leave_balance(employee, leave_type, today).get("remaining_hours"), 2)
        else:
            from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
            remaining = flt(get_leave_balance_on(employee, leave_type, today, consider_all_leaves_in_the_allocation_period=True), 2)
        item.update({"unit": unit, "remaining": remaining, "used": max(0, flt(item["allocated"] - remaining, 2))})
        balances.append(item)

    attendance_fields = ["name", "attendance_date", "status", "in_time", "out_time", "working_hours", "late_entry", "early_exit"]
    meta = frappe.get_meta("Attendance")
    for fieldname in ("custom_check_in_branch", "custom_check_out_branch"):
        if meta.has_field(fieldname):
            attendance_fields.append(fieldname)
    attendance = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "docstatus": ["<", 2],
            "attendance_date": ["between", [period_start, period_end]],
        },
        fields=attendance_fields,
        order_by="attendance_date desc",
        limit_page_length=0,
    )
    return {
        "balances": balances,
        "attendance": attendance,
        "attendance_period": {"month": month, "year": year, "from_date": period_start, "to_date": period_end},
    }
