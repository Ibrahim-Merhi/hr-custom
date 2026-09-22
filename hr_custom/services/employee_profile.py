import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def _employee(name):
    doc = frappe.get_doc("Employee", name)
    doc.check_permission("read")
    return doc


@frappe.whitelist()
def get_employee_hr_history(employee):
    _employee(employee)
    today = getdate(nowdate())
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
        filters={"employee": employee, "docstatus": ["<", 2]},
        fields=attendance_fields,
        order_by="attendance_date desc",
        limit=100,
    )
    return {"balances": balances, "attendance": attendance}
