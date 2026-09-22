import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    conditions = ["attendance_date between %(from_date)s and %(to_date)s"]
    values = {"from_date": filters.from_date, "to_date": filters.to_date}
    for field in ("employee", "branch", "exception_type", "status"):
        if filters.get(field):
            conditions.append(f"{field}=%({field})s")
            values[field] = filters[field]

    rows = frappe.db.sql(
        f"""select name, employee, attendance_date, exception_type, details, branch,
            shift_type, first_checkin, last_checkout, working_hours, status,
            resolved_by, resolved_on, resolution_notes
        from `tabAttendance Exception`
        where {' and '.join(conditions)}
        order by status asc, attendance_date desc, employee asc""",
        values,
        as_dict=True,
    )
    if rows:
        corrections = frappe.get_all(
            "Attendance Correction Request",
            filters={
                "employee": ["in", list({row.employee for row in rows})],
                "attendance_date": ["between", [filters.from_date, filters.to_date]],
                "docstatus": ["<", 2],
            },
            fields=["name", "employee", "attendance_date", "status", "approval_stage", "creation"],
            order_by="creation desc",
        )
        latest = {}
        for correction in corrections:
            latest.setdefault((correction.employee, str(correction.attendance_date)), correction)
        for row in rows:
            correction = latest.get((row.employee, str(row.attendance_date)))
            row.correction_request = correction.name if correction else None
            row.correction_status = (correction.approval_stage or correction.status) if correction else None

    columns = [
        ("name", "Exception", "Link", "Attendance Exception", 150),
        ("employee", "Employee", "Link", "Employee", 130),
        ("attendance_date", "Date", "Date", None, 105),
        ("exception_type", "Abnormal Type", "Data", None, 160),
        ("details", "Details", "Data", None, 260),
        ("branch", "Branch", "Link", "Branch", 120),
        ("shift_type", "Shift", "Link", "Shift Type", 120),
        ("working_hours", "Working Hours", "Float", None, 110),
        ("status", "Resolution", "Data", None, 100),
        ("correction_request", "Correction Request", "Link", "Attendance Correction Request", 170),
        ("correction_status", "Correction Status", "Data", None, 165),
        ("resolution_notes", "Resolution Notes", "Data", None, 220),
    ]
    return [
        {"fieldname": field, "label": _(label), "fieldtype": fieldtype, "options": options, "width": width}
        for field, label, fieldtype, options, width in columns
    ], rows
