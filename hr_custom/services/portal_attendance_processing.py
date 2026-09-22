import frappe
from frappe.utils import add_days, flt, getdate


def finalize_checkin_pair(doc, method=None):
    """Create/update attendance as soon as an OUT completes a same-day pair."""
    if doc.log_type != "OUT" or doc.skip_auto_attendance:
        return
    return finalize_completed_day(doc.employee, getdate(doc.time))


@frappe.whitelist(methods=["POST"])
def finalize_completed_day(employee, attendance_date):
    """Temporary simple rule: any same-date IN then OUT is Present."""
    user = frappe.session.user
    privileged_roles = {"System Manager", "HR Manager", "HR User"}
    if user != "Administrator" and not privileged_roles.intersection(frappe.get_roles(user)):
        own_employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
        if own_employee != employee:
            frappe.throw(
                frappe._("You can only process attendance for your own employee record."),
                frappe.PermissionError,
            )
    attendance_date = getdate(attendance_date)
    existing = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": attendance_date, "docstatus": 1},
        "name",
    )
    logs = frappe.get_all(
        "Employee Checkin",
        filters=[
            ["employee", "=", employee],
            ["time", ">=", attendance_date],
            ["time", "<", add_days(attendance_date, 1)],
            ["skip_auto_attendance", "=", 0],
        ],
        fields=["name", "employee", "time", "log_type", "shift"],
        order_by="time asc",
    )
    first_in = next((row for row in logs if row.log_type == "IN"), None)
    last_out = next((row for row in reversed(logs) if row.log_type == "OUT"), None)
    if not first_in or not last_out or last_out.time <= first_in.time:
        return None

    worked = flt((last_out.time - first_in.time).total_seconds() / 3600, 2)
    shift = first_in.shift or last_out.shift
    if existing:
        if frappe.db.get_value("Attendance", existing, "status") != "Present":
            return frappe.get_doc("Attendance", existing)
        frappe.db.set_value(
            "Attendance",
            existing,
            {"in_time": first_in.time, "out_time": last_out.time, "working_hours": worked, "shift": shift},
            update_modified=False,
        )
        for row in logs:
            if not frappe.db.get_value("Employee Checkin", row.name, "attendance"):
                frappe.db.set_value("Employee Checkin", row.name, "attendance", existing, update_modified=False)
        return frappe.get_doc("Attendance", existing)

    from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
    return mark_attendance_and_link_log(
        logs,
        "Present",
        attendance_date,
        working_hours=worked,
        in_time=first_in.time,
        out_time=last_out.time,
        shift=shift,
    )


def reconcile_recent_completed_pairs(days=3):
    """Recover completed punch pairs missed by a stale hook or interrupted job."""
    dates = frappe.db.sql(
        """
        select distinct employee, date(time) as attendance_date
        from `tabEmployee Checkin`
        where time >= %s
          and ifnull(skip_auto_attendance, 0) = 0
          and log_type = 'OUT'
          and ifnull(attendance, '') = ''
        order by attendance_date asc
        """,
        [add_days(getdate(), -int(days))],
        as_dict=True,
    )
    created = []
    for row in dates:
        attendance = finalize_completed_day(row.employee, row.attendance_date)
        if attendance:
            created.append(attendance.name)
    return created


def ensure_dynamic_checkin_event():
    """Install an immediately active event for deployments awaiting restart."""
    name = "Create Attendance From Completed Checkin Pair"
    values = {
        "script_type": "DocType Event",
        "reference_doctype": "Employee Checkin",
        "doctype_event": "After Insert",
        "disabled": 0,
        "script": """if doc.log_type == 'OUT' and not doc.skip_auto_attendance:\n    frappe.call('hr_custom.services.portal_attendance_processing.finalize_completed_day', employee=doc.employee, attendance_date=str(doc.time)[:10])""",
    }
    if frappe.db.exists("Server Script", name):
        server_script = frappe.get_doc("Server Script", name)
        server_script.update(values)
        server_script.save(ignore_permissions=True)
    else:
        server_script = frappe.get_doc({"doctype": "Server Script", "name": name, **values})
        server_script.insert(ignore_permissions=True)
    frappe.cache.delete_value("server_script_map")
    return server_script.name
