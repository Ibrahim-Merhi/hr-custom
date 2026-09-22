import frappe


def populate_attendance_branches(doc, method=None):
    """Copy the first IN and last OUT punch branches onto Attendance."""
    if not doc.employee or not doc.attendance_date:
        return
    rows = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": doc.employee,
            "time": ["between", [f"{doc.attendance_date} 00:00:00", f"{doc.attendance_date} 23:59:59"]],
        },
        fields=["log_type", "custom_branch"],
        order_by="time asc",
    )
    check_in = next((row.custom_branch for row in rows if row.log_type == "IN" and row.custom_branch), None)
    check_out = next((row.custom_branch for row in reversed(rows) if row.log_type == "OUT" and row.custom_branch), None)
    if doc.meta.has_field("custom_check_in_branch"):
        doc.custom_check_in_branch = check_in
        doc.custom_check_out_branch = check_out


def backfill_attendance_branches():
    for name in frappe.get_all("Attendance", filters={"docstatus": ["<", 2]}, pluck="name"):
        doc = frappe.get_doc("Attendance", name)
        before = (doc.custom_check_in_branch, doc.custom_check_out_branch)
        populate_attendance_branches(doc)
        after = (doc.custom_check_in_branch, doc.custom_check_out_branch)
        if after != before:
            frappe.db.set_value("Attendance", name, {"custom_check_in_branch": after[0], "custom_check_out_branch": after[1]}, update_modified=False)
    return {"updated": True}
