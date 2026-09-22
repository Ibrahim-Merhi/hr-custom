import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    values = {"as_of_date": getdate(filters.as_of_date)}
    conditions = [
        "la.docstatus = 1",
        "la.expired = 0",
        "la.from_date <= %(as_of_date)s",
        "la.to_date >= %(as_of_date)s",
        "lt.custom_leave_unit = 'Hours'",
    ]
    for field, column in (("company", "e.company"), ("employee", "la.employee"), ("leave_type", "la.leave_type")):
        if filters.get(field):
            conditions.append(f"{column} = %({field})s")
            values[field] = filters[field]

    data = frappe.db.sql(
        f"""
        SELECT
            allocation.employee,
            allocation.employee_name,
            allocation.company,
            allocation.leave_type,
            allocation.allocated_hours,
            COALESCE((
                SELECT SUM(app.custom_leave_hours)
                FROM `tabLeave Application` app
                WHERE app.employee = allocation.employee
                  AND app.leave_type = allocation.leave_type
                  AND app.docstatus = 1
                  AND app.status = 'Approved'
                  AND app.custom_leave_unit = 'Hours'
                  AND app.to_date >= allocation.allocation_from
                  AND app.from_date <= allocation.allocation_to
            ), 0) AS used_hours
        FROM (
            SELECT la.employee, e.employee_name, e.company, la.leave_type,
                   SUM(la.total_leaves_allocated) AS allocated_hours,
                   MIN(la.from_date) AS allocation_from,
                   MAX(la.to_date) AS allocation_to
            FROM `tabLeave Allocation` la
            INNER JOIN `tabEmployee` e ON e.name = la.employee
            INNER JOIN `tabLeave Type` lt ON lt.name = la.leave_type
            WHERE {' AND '.join(conditions)}
            GROUP BY la.employee, e.employee_name, e.company, la.leave_type
        ) allocation
        ORDER BY allocation.employee_name, allocation.leave_type
        """,
        values,
        as_dict=True,
    )
    for row in data:
        row.remaining_hours = row.allocated_hours - row.used_hours
    return _columns(), data


def _columns():
    return [
        {"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 130},
        {"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 160},
        {"fieldname": "leave_type", "label": _("Leave Type"), "fieldtype": "Link", "options": "Leave Type", "width": 170},
        {"fieldname": "allocated_hours", "label": _("Allocated Hours"), "fieldtype": "Float", "precision": 2, "width": 120},
        {"fieldname": "used_hours", "label": _("Used Hours"), "fieldtype": "Float", "precision": 2, "width": 110},
        {"fieldname": "remaining_hours", "label": _("Remaining Hours"), "fieldtype": "Float", "precision": 2, "width": 130},
    ]
