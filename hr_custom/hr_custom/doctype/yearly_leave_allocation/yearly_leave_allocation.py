import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

from hr_custom.services.yearly_leave_allocation import (
    cancel_generated_allocations,
    enqueue_generation,
    validate_master,
)


class YearlyLeaveAllocation(Document):
    def validate(self):
        validate_master(self, strict=self.docstatus == 1)

    def before_submit(self):
        if not {"HR Manager", "System Manager"}.intersection(frappe.get_roles()):
            frappe.throw(_("Only an HR Manager can submit yearly leave allocations."), frappe.PermissionError)
        validate_master(self, strict=True)
        self.status = "Processing"

    def on_submit(self):
        enqueue_generation(self.name)

    def on_update_after_submit(self):
        if not {"HR Manager", "System Manager"}.intersection(frappe.get_roles()):
            frappe.throw(_("Only an HR Manager can change submitted leave allocations."), frappe.PermissionError)
        validate_master(self, strict=True)
        frappe.db.set_value(self.doctype, self.name, "status", "Processing", update_modified=False)
        enqueue_generation(self.name)

    def before_cancel(self):
        if self.status == "Processing":
            frappe.throw(_("Please wait until allocation processing is complete before cancelling."))
        cancel_generated_allocations(self)
        self.status = "Cancelled"


@frappe.whitelist(methods=["POST"])
def generate_employees(name):
    doc = frappe.get_doc("Yearly Leave Allocation", name)
    doc.check_permission("write")
    if doc.docstatus:
        frappe.throw(_("Employees can only be generated in Draft."))
    filters = {"company": doc.company, "status": "Active"}
    for field in ("branch", "department", "employment_type", "designation"):
        value = doc.get(f"filter_{field}")
        if value:
            filters[field] = value
    existing = {row.employee for row in doc.employees}
    rows = frappe.get_all("Employee", filters=filters, fields=["name", "employee_name", "attendance_device_id", "department", "branch", "designation", "employment_type", "status"], order_by="employee_name asc")
    for row in rows:
        if row.name not in existing:
            doc.append("employees", {"employee": row.name, "employee_name": row.employee_name, "attendance_device_id": row.attendance_device_id, "department": row.department, "branch": row.branch, "designation": row.designation, "employment_type": row.employment_type, "is_active": 1})
    doc.save()
    return {"added": len(rows) - len(existing.intersection({r.name for r in rows})), "total": len(doc.employees)}


@frappe.whitelist(methods=["POST"])
def generate_allowances(name):
    doc = frappe.get_doc("Yearly Leave Allocation", name)
    doc.check_permission("write")
    if doc.docstatus:
        frappe.throw(_("Allowances can only be generated in Draft."))
    leave_types = frappe.get_all("Leave Type", filters={"is_lwp": 0}, fields=["name", "custom_leave_unit"], order_by="name")
    existing = {(row.employee, row.leave_type, str(row.from_date), str(row.to_date)) for row in doc.allocations}
    added = 0
    for employee in (row.employee for row in doc.employees if not row.exclude_from_allocation):
        for leave_type in leave_types:
            key = (employee, leave_type.name, str(doc.from_date), str(doc.to_date))
            if key in existing:
                continue
            doc.append("allocations", {"employee": employee, "employee_name": frappe.db.get_value("Employee", employee, "employee_name"), "leave_type": leave_type.name, "leave_unit": leave_type.custom_leave_unit or "Days", "allocated_amount": 0, "from_date": doc.from_date, "to_date": doc.to_date, "allocation_status": "Pending"})
            existing.add(key)
            added += 1
    doc.save()
    return {"added": added, "total": len(doc.allocations)}


@frappe.whitelist(methods=["POST"])
def copy_previous_year(name):
    doc = frappe.get_doc("Yearly Leave Allocation", name)
    doc.check_permission("write")
    if doc.docstatus or doc.allocations:
        frappe.throw(_("Copy Previous Year requires a Draft with no allowance rows."))
    previous = frappe.db.get_value("Yearly Leave Allocation", {"company": doc.company, "allocation_year": cint(doc.allocation_year) - 1, "docstatus": ["<", 2]}, "name", order_by="modified desc")
    if not previous:
        frappe.throw(_("No previous-year allocation was found for this company."))
    source = frappe.get_doc("Yearly Leave Allocation", previous)
    for row in source.employees:
        doc.append("employees", {key: row.get(key) for key in ("employee", "employee_name", "attendance_device_id", "department", "branch", "designation", "employment_type", "is_active", "exclude_from_allocation", "remarks")})
    for row in source.allocations:
        doc.append("allocations", {"employee": row.employee, "employee_name": row.employee_name or frappe.db.get_value("Employee", row.employee, "employee_name"), "leave_type": row.leave_type, "leave_unit": row.leave_unit, "allocated_amount": row.allocated_amount, "from_date": doc.from_date, "to_date": doc.to_date, "allocation_status": "Pending", "legacy_employee_code": row.legacy_employee_code, "legacy_leave_type_code": row.legacy_leave_type_code, "migration_source": row.migration_source})
    doc.save()
    return {"source": previous, "employees": len(doc.employees), "allocations": len(doc.allocations)}


@frappe.whitelist()
def preview(name):
    doc = frappe.get_doc("Yearly Leave Allocation", name)
    doc.check_permission("read")
    errors = validate_master(doc, strict=False)
    positive = [row for row in doc.allocations if flt(row.allocated_amount) > 0]
    return {"year": doc.allocation_year, "employees": len([r for r in doc.employees if not r.exclude_from_allocation]), "allocations": len(doc.allocations), "day_rows": len([r for r in positive if r.leave_unit == "Days"]), "hour_rows": len([r for r in positive if r.leave_unit == "Hours"]), "ready": len(positive) - len(errors), "errors": errors}


@frappe.whitelist(methods=["POST"])
def create_supplemental_allocation(name, employee, from_date):
    source = frappe.get_doc("Yearly Leave Allocation", name)
    source.check_permission("read")
    if source.docstatus != 1:
        frappe.throw(_("A supplemental allocation can only be created from a submitted yearly allocation."))
    if not {"HR Manager", "System Manager"}.intersection(frappe.get_roles()):
        frappe.throw(_("Only an HR Manager can create supplemental allocations."), frappe.PermissionError)

    employee_doc = frappe.get_doc("Employee", employee)
    if employee_doc.company != source.company or employee_doc.status != "Active":
        frappe.throw(_("Select an active employee from {0}.").format(source.company))
    start = getdate(from_date)
    if start < getdate(source.from_date) or start > getdate(source.to_date):
        frappe.throw(_("Allocation start date must be within the source allocation period."))

    supplemental = frappe.get_doc({
        "doctype": "Yearly Leave Allocation",
        "company": source.company,
        "allocation_year": source.allocation_year,
        "from_date": start,
        "to_date": source.to_date,
        "description": _("Supplemental allocation for {0}, based on {1}").format(employee_doc.employee_name, source.name),
    })
    supplemental.append("employees", {
        "employee": employee_doc.name,
        "employee_name": employee_doc.employee_name,
        "attendance_device_id": employee_doc.attendance_device_id,
        "department": employee_doc.department,
        "branch": employee_doc.branch,
        "designation": employee_doc.designation,
        "employment_type": employee_doc.employment_type,
        "is_active": 1,
    })
    leave_types = {}
    for row in source.allocations:
        leave_types.setdefault(row.leave_type, row.leave_unit)
    for leave_type, leave_unit in sorted(leave_types.items()):
        supplemental.append("allocations", {
            "employee": employee_doc.name,
            "employee_name": employee_doc.employee_name,
            "leave_type": leave_type,
            "leave_unit": leave_unit,
            "allocated_amount": 0,
            "from_date": start,
            "to_date": source.to_date,
            "allocation_status": "Pending",
        })
    supplemental.insert()
    return {"name": supplemental.name}
