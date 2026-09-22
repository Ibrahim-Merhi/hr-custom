import csv
import io
import traceback

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def _conflict(row, master_name=None):
    filters = {"employee": row.employee, "leave_type": row.leave_type, "docstatus": ["<", 2], "from_date": ["<=", row.to_date], "to_date": [">=", row.from_date]}
    names = frappe.get_all("Leave Allocation", filters=filters, pluck="name")
    if row.standard_leave_allocation in names:
        names.remove(row.standard_leave_allocation)
    if master_name and names:
        names = [name for name in names if frappe.db.get_value("Leave Allocation", name, "custom_yearly_leave_allocation") != master_name]
    return names[0] if names else None


def _exact_unlinked_allocations(row, master_name):
    """Return exact allocations that can safely be adopted by this master."""
    allocations = frappe.get_all(
        "Leave Allocation",
        filters={
            "employee": row.employee,
            "leave_type": row.leave_type,
            "from_date": row.from_date,
            "to_date": row.to_date,
            "docstatus": ["<", 2],
        },
        fields=[
            "name",
            "new_leaves_allocated",
            "docstatus",
            "custom_yearly_leave_allocation",
            "custom_yearly_leave_allocation_detail",
        ],
        order_by="creation asc",
    )
    return [
        allocation
        for allocation in allocations
        if flt(allocation.new_leaves_allocated) == flt(row.allocated_amount)
        and allocation.custom_yearly_leave_allocation in (None, "", master_name)
        and allocation.custom_yearly_leave_allocation_detail in (None, "", row.name)
    ]


@frappe.whitelist(methods=["POST"])
def link_existing_allocations(name):
    """Adopt unique, exact Leave Allocations instead of generating duplicates."""
    doc = frappe.get_doc("Yearly Leave Allocation", name)
    doc.check_permission("write")
    if doc.docstatus != 0:
        frappe.throw(_("Existing allocations can only be linked while the yearly allocation is in Draft."))

    allocation_meta = frappe.get_meta("Leave Allocation")
    linked = already_linked = ambiguous = 0
    unresolved = []

    for row in doc.allocations:
        if flt(row.allocated_amount) <= 0:
            continue
        if row.standard_leave_allocation and frappe.db.exists("Leave Allocation", row.standard_leave_allocation):
            already_linked += 1
            continue

        matches = _exact_unlinked_allocations(row, doc.name)
        if len(matches) != 1:
            if len(matches) > 1:
                ambiguous += 1
                unresolved.append(
                    _("Row {0}: multiple exact Leave Allocations exist ({1}).").format(
                        row.idx, ", ".join(allocation.name for allocation in matches)
                    )
                )
            continue

        allocation = matches[0]
        values = {}
        if allocation_meta.has_field("custom_yearly_leave_allocation"):
            values["custom_yearly_leave_allocation"] = doc.name
        if allocation_meta.has_field("custom_yearly_leave_allocation_detail"):
            values["custom_yearly_leave_allocation_detail"] = row.name
        if values:
            frappe.db.set_value("Leave Allocation", allocation.name, values, update_modified=False)
        frappe.db.set_value(
            row.doctype,
            row.name,
            {
                "standard_leave_allocation": allocation.name,
                "allocation_status": "Submitted" if allocation.docstatus == 1 else "Created",
                "error_message": "",
            },
            update_modified=False,
        )
        linked += 1

    frappe.db.commit()
    return {
        "linked": linked,
        "already_linked": already_linked,
        "ambiguous": ambiguous,
        "unresolved": unresolved,
    }


@frappe.whitelist(methods=["POST"])
def consolidate_duplicate_rows(name):
    """Merge additive legacy vouchers for the same employee/type/period."""
    doc = frappe.get_doc("Yearly Leave Allocation", name)
    doc.check_permission("write")
    if doc.docstatus != 0:
        frappe.throw(_("Duplicate rows can only be consolidated while the yearly allocation is in Draft."))

    groups = {}
    for row in doc.allocations:
        key = (row.employee, row.leave_type, str(row.from_date), str(row.to_date))
        groups.setdefault(key, []).append(row)

    merged = 0
    removed_rows = []
    removed_allocations = []
    for rows in groups.values():
        if len(rows) < 2:
            continue

        allocations = []
        for row in rows:
            if row.standard_leave_allocation and frappe.db.exists("Leave Allocation", row.standard_leave_allocation):
                allocation = frappe.get_doc("Leave Allocation", row.standard_leave_allocation)
                if allocation.docstatus != 0:
                    frappe.throw(
                        _("Rows {0} cannot be consolidated because Leave Allocation {1} is submitted.").format(
                            ", ".join(str(item.idx) for item in rows), allocation.name
                        )
                    )
                allocations.append(allocation)

        canonical = rows[0]
        canonical.allocated_amount = sum(flt(row.allocated_amount) for row in rows)
        canonical.allocation_status = "Pending"
        canonical.standard_leave_allocation = None
        canonical.error_message = ""
        for duplicate in rows[1:]:
            removed_rows.append(duplicate.name)
            doc.remove(duplicate)

        for allocation in allocations:
            removed_allocations.append(allocation.name)
        merged += 1

    doc.save()
    # Saving first removes the child-table links that protect these superseded
    # drafts from deletion. The whole request remains one database transaction.
    for allocation_name in removed_allocations:
        frappe.delete_doc("Leave Allocation", allocation_name, ignore_permissions=True)
    return {
        "merged": merged,
        "removed_rows": len(removed_rows),
        "removed_allocations": len(removed_allocations),
    }


def remove_unpaid_leave_allocation_rows(name):
    """Remove invalid LWP rows from one allocation while retaining history."""
    doc = frappe.get_doc("Yearly Leave Allocation", name)
    unpaid_types = frappe.get_all("Leave Type", filters={"is_lwp": 1}, pluck="name")
    if not unpaid_types:
        return {"removed": 0, "master": name}
    rows = frappe.get_all(
        "Yearly Leave Allocation Detail",
        filters={"parent": doc.name, "leave_type": ["in", unpaid_types]},
        fields=["name", "parent", "standard_leave_allocation"],
    )
    linked = [row.standard_leave_allocation for row in rows if row.standard_leave_allocation]
    if linked:
        frappe.throw(
            _("Cannot remove Unpaid Leave rows because these Leave Allocations are linked: {0}").format(
                ", ".join(linked)
            )
        )
    if rows:
        frappe.db.delete("Yearly Leave Allocation Detail", {"name": ["in", [row.name for row in rows]]})
    total = frappe.db.count(
        "Yearly Leave Allocation Detail",
        {"parent": doc.name, "allocated_amount": [">", 0]},
    )
    frappe.db.set_value("Yearly Leave Allocation", doc.name, "total_allocations", total, update_modified=False)
    return {"removed": len(rows), "master": doc.name}


def enable_hourly_leave_for_failed_rows(name):
    """Enable Both units only for employees with imported failed hour rows."""
    doc = frappe.get_doc("Yearly Leave Allocation", name)
    employees = sorted({
        row.employee
        for row in doc.allocations
        if row.allocation_status == "Failed" and row.leave_unit == "Hours"
    })
    for employee in employees:
        frappe.db.set_value(
            "Employee",
            employee,
            "custom_leave_calculation_mode_override",
            "Both",
            update_modified=False,
        )
    return {"updated": len(employees), "employees": employees}


def validate_master(doc, strict=False):
    errors, seen = [], set()
    if getdate(doc.from_date) > getdate(doc.to_date):
        errors.append(_("From Date must be before To Date."))
    if getdate(doc.from_date).year != cint(doc.allocation_year) or getdate(doc.to_date).year != cint(doc.allocation_year):
        errors.append(_("From Date and To Date must belong to the Allocation Year."))
    employees = {r.name: r for r in frappe.get_all("Employee", filters={"name": ["in", list({x.employee for x in doc.allocations}) or [""]]}, fields=["name", "company", "status"])}
    leave_types = {r.name: r.custom_leave_unit for r in frappe.get_all("Leave Type", filters={"name": ["in", list({x.leave_type for x in doc.allocations}) or [""]]}, fields=["name", "custom_leave_unit"])}
    for index, row in enumerate(doc.allocations, 1):
        key = (row.employee, row.leave_type, str(row.from_date), str(row.to_date))
        if key in seen: errors.append(_("Row {0}: duplicate employee, leave type and period.").format(index))
        seen.add(key)
        employee = employees.get(row.employee)
        if not employee: errors.append(_("Row {0}: employee does not exist.").format(index)); continue
        row.employee_name = frappe.db.get_value("Employee", row.employee, "employee_name")
        if employee.company != doc.company: errors.append(_("Row {0}: employee belongs to another company.").format(index))
        if employee.status != "Active": errors.append(_("Row {0}: employee is not active.").format(index))
        unit = leave_types.get(row.leave_type)
        if unit not in ("Days", "Hours"): errors.append(_("Row {0}: leave unit is not configured.").format(index))
        else: row.leave_unit = unit
        if flt(row.allocated_amount) < 0: errors.append(_("Row {0}: allocated amount cannot be negative.").format(index))
        if getdate(row.from_date) > getdate(row.to_date): errors.append(_("Row {0}: invalid period.").format(index))
        conflict = _conflict(row, doc.name)
        if conflict: errors.append(_("Row {0}: conflicts with Leave Allocation {1}.").format(index, conflict))
    doc.total_employees = len({r.employee for r in doc.employees if not r.exclude_from_allocation})
    doc.total_allocations = len([r for r in doc.allocations if flt(r.allocated_amount) > 0])
    if doc.docstatus == 0 and not errors:
        doc.status = "Ready" if doc.total_allocations else "Draft"
    if strict and errors:
        frappe.throw("<br>".join(errors[:50]), title=_("Yearly Leave Allocation Validation"))
    return errors


def enqueue_generation(name):
    frappe.enqueue("hr_custom.services.yearly_leave_allocation.generate_standard_allocations", queue="long", enqueue_after_commit=True, job_name=f"yearly_leave_allocation::{name}", name=name)


def generate_standard_allocations(name):
    doc = frappe.get_doc("Yearly Leave Allocation", name)
    if doc.docstatus != 1: return
    success = failed = 0
    meta = frappe.get_meta("Leave Allocation")
    for row in doc.allocations:
        if flt(row.allocated_amount) <= 0:
            frappe.db.set_value(row.doctype, row.name, {"allocation_status": "Skipped", "error_message": ""})
            continue
        try:
            if row.standard_leave_allocation and frappe.db.exists("Leave Allocation", row.standard_leave_allocation):
                allocation = frappe.get_doc("Leave Allocation", row.standard_leave_allocation)
                if allocation.docstatus == 1:
                    if flt(allocation.new_leaves_allocated) != flt(row.allocated_amount):
                        allocation.new_leaves_allocated = row.allocated_amount
                        allocation.flags.ignore_permissions = True
                        allocation.save()
                    frappe.db.set_value(row.doctype, row.name, {"allocation_status":"Submitted", "error_message":""})
                    success += 1
                    continue
            generated = frappe.db.get_value(
                "Leave Allocation",
                {"custom_yearly_leave_allocation": doc.name, "custom_yearly_leave_allocation_detail": row.name, "docstatus": ["<", 2]},
                "name",
            )
            if generated:
                allocation = frappe.get_doc("Leave Allocation", generated)
                frappe.db.set_value(row.doctype, row.name, "standard_leave_allocation", generated)
                if allocation.docstatus == 0:
                    allocation.submit()
                frappe.db.set_value(row.doctype, row.name, {"allocation_status":"Submitted", "error_message":""})
                success += 1
                frappe.db.commit()
                continue
            conflict = _conflict(row, doc.name)
            if conflict: raise frappe.ValidationError(_("Conflicting Leave Allocation {0}").format(conflict))
            values = {"doctype":"Leave Allocation", "employee":row.employee, "leave_type":row.leave_type, "from_date":row.from_date, "to_date":row.to_date, "new_leaves_allocated":row.allocated_amount, "carry_forward":0}
            if meta.has_field("company"): values["company"] = doc.company
            if meta.has_field("custom_yearly_leave_allocation"): values["custom_yearly_leave_allocation"] = doc.name
            if meta.has_field("custom_yearly_leave_allocation_detail"): values["custom_yearly_leave_allocation_detail"] = row.name
            allocation = frappe.get_doc(values).insert(ignore_permissions=True)
            frappe.db.set_value(row.doctype, row.name, {"standard_leave_allocation": allocation.name, "allocation_status":"Created", "error_message":""})
            allocation.submit()
            frappe.db.set_value(row.doctype, row.name, {"allocation_status":"Submitted", "error_message":""})
            success += 1
        except Exception as error:
            failed += 1
            frappe.db.rollback()
            frappe.db.set_value(row.doctype, row.name, {"allocation_status":"Failed", "error_message":str(error)[:500]})
            frappe.log_error(traceback.format_exc(), f"Yearly Leave Allocation {name}: {row.employee} / {row.leave_type}")
        frappe.db.commit()
    status = "Completed" if success and not failed else "Partially Completed" if success else "Failed"
    frappe.db.set_value("Yearly Leave Allocation", name, {"status":status, "successful_allocations":success, "failed_allocations":failed, "allocation_generated":1 if success else 0})
    frappe.db.commit()


def cancel_generated_allocations(doc):
    blockers = []
    for row in doc.allocations:
        if not row.standard_leave_allocation or not frappe.db.exists("Leave Allocation", row.standard_leave_allocation): continue
        allocation = frappe.get_doc("Leave Allocation", row.standard_leave_allocation)
        if allocation.docstatus == 1:
            try: allocation.cancel()
            except Exception as error: blockers.append(f"{allocation.name}: {error}")
        if allocation.docstatus == 2:
            frappe.db.set_value(row.doctype, row.name, "allocation_status", "Cancelled")
    if blockers: frappe.throw("<br>".join(blockers), title=_("Generated allocations could not be cancelled"))


@frappe.whitelist(methods=["POST"])
def retry_generation(name):
    doc = frappe.get_doc("Yearly Leave Allocation", name); doc.check_permission("submit")
    if doc.docstatus != 1 or doc.status == "Processing": frappe.throw(_("This document cannot be retried now."))
    frappe.db.set_value(doc.doctype, doc.name, "status", "Processing")
    enqueue_generation(name)


@frappe.whitelist(methods=["POST"])
def import_normalized_csv(content, source_name="Normalized CSV"):
    if not {"HR Manager", "System Manager"}.intersection(frappe.get_roles()): frappe.throw(_("Only HR Manager can import yearly allocations."), frappe.PermissionError)
    rows = list(csv.DictReader(io.StringIO(content)))
    employee_map = {r.attendance_device_id:r for r in frappe.get_all("Employee", filters={"attendance_device_id":["is","set"]}, fields=["name","employee_name","attendance_device_id","company","department","branch","designation","employment_type","status"])}
    leave_map = {r.custom_legacy_leave_type_code:r for r in frappe.get_all("Leave Type", filters={"custom_legacy_leave_type_code":["is","set"], "is_lwp": 0}, fields=["name","custom_legacy_leave_type_code","custom_leave_unit"])}
    masters, exceptions = {}, []
    for number, raw in enumerate(rows, 2):
        code = (raw.get("Legacy Employee Code") or "").strip(); legacy_type = (raw.get("Legacy Leave Type Code") or "").strip()
        employee = employee_map.get(code); leave_type = leave_map.get(legacy_type)
        if not employee or not leave_type:
            exceptions.append({"row":number,"legacy_employee_code":code,"leave_type":legacy_type or raw.get("Leave Type"),"amount":raw.get("Allocated Amount"),"reason":_("No Employee found with Attendance Device ID {0}").format(code) if not employee else _("No Leave Type found for legacy code {0}").format(legacy_type)}); continue
        start, end = getdate(raw.get("From Date") or raw.get("Period Starting")), getdate(raw.get("To Date") or f"{getdate(raw.get('Period Starting')).year}-12-31")
        key = (employee.company, start.year, start, end)
        if key not in masters:
            masters[key] = frappe.get_doc({"doctype":"Yearly Leave Allocation","company":employee.company,"allocation_year":start.year,"from_date":start,"to_date":end,"description":f"Imported from {source_name}"})
        master = masters[key]
        if employee.name not in {r.employee for r in master.employees}: master.append("employees", {"employee":employee.name,"employee_name":employee.employee_name,"attendance_device_id":code,"department":employee.department,"branch":employee.branch,"designation":employee.designation,"employment_type":employee.employment_type,"is_active":employee.status == "Active"})
        amount = flt(raw.get("Allocated Amount") or raw.get("Leave Days"))
        existing_allocation = next(
            (
                row
                for row in master.allocations
                if row.employee == employee.name
                and row.leave_type == leave_type.name
                and getdate(row.from_date) == start
                and getdate(row.to_date) == end
            ),
            None,
        )
        if existing_allocation:
            existing_allocation.allocated_amount = flt(existing_allocation.allocated_amount) + amount
        else:
            master.append("allocations", {"employee":employee.name,"employee_name":employee.employee_name,"leave_type":leave_type.name,"leave_unit":leave_type.custom_leave_unit,"allocated_amount":amount,"from_date":start,"to_date":end,"allocation_status":"Pending","legacy_employee_code":code,"legacy_leave_type_code":legacy_type,"migration_source":source_name})
    names = [doc.insert(ignore_permissions=True).name for doc in masters.values()]
    return {"masters":names,"imported":sum(len(d.allocations) for d in masters.values()),"exceptions":exceptions}


def backfill_allocation_employee_names():
    frappe.db.sql("""update `tabYearly Leave Allocation Detail` d join `tabEmployee` e on e.name=d.employee set d.employee_name=e.employee_name where ifnull(d.employee_name, '')=''""")
    return frappe.db.count("Yearly Leave Allocation Detail", {"employee_name": ["is", "set"]})
