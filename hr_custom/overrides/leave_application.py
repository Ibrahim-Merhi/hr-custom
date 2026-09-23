import frappe
from frappe import _
from frappe.utils import cint, flt, getdate
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry

from hr_custom.services.hourly_leave import apply_calculation, validate_hour_balance
from hr_custom.services.work_schedule import get_leave_unit, validate_unit_eligibility

MIGRATED_RECORD_FIELD = "custom_is_migrated_record"
HISTORICAL_LEAVE_START = getdate("2022-01-01")
HISTORICAL_LEAVE_END = getdate("2026-12-31")


class HourlyLeaveApplication(LeaveApplication):
    """Use HRMS unchanged for day leave and extend only hour-based Leave Types."""

    def is_historical_migration(self):
        return cint(self.get(MIGRATED_RECORD_FIELD)) == 1

    def validate(self):
        if not self.is_historical_migration():
            return super().validate()

        self._validate_historical_migration()

    def _validate_historical_migration(self):
        """Validate only migration invariants without applying today's leave policy."""
        if not self.from_date or not self.to_date:
            frappe.throw(_("From Date and To Date are required for migrated leave applications."))

        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        if to_date < from_date:
            frappe.throw(_("To date cannot be before from date"))
        if from_date < HISTORICAL_LEAVE_START or to_date > HISTORICAL_LEAVE_END:
            frappe.throw(
                _("Migrated leave applications must be dated between {0} and {1}.").format(
                    HISTORICAL_LEAVE_START, HISTORICAL_LEAVE_END
                )
            )

        self._validate_legacy_voucher_number()
        self.status = "Approved"

        # Employee Name is mandatory in HRMS, but do not overwrite an imported value.
        if self.employee and not self.employee_name:
            self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")

    def _validate_legacy_voucher_number(self):
        voucher_number = (self.custom_legacy_voucher_number or "").strip()
        self.custom_legacy_voucher_number = voucher_number
        if not voucher_number:
            return

        filters = {"custom_legacy_voucher_number": voucher_number}
        if self.name:
            filters["name"] = ["!=", self.name]
        duplicate = frappe.db.get_value("Leave Application", filters, "name")
        if duplicate:
            frappe.throw(
                _("Legacy Voucher Number {0} was already imported in Leave Application {1}.").format(
                    frappe.bold(voucher_number), frappe.bold(duplicate)
                )
            )

    def after_insert(self):
        if self.is_historical_migration():
            return
        return super().after_insert()

    def on_update(self):
        if self.is_historical_migration():
            return
        return super().on_update()

    def on_submit(self):
        if self.is_historical_migration():
            self.create_leave_ledger_entry()
            return
        return super().on_submit()

    def validate_balance_leaves(self):
        if self.is_historical_migration():
            return

        result = apply_calculation(self)
        if result["leave_unit"] != "Hours":
            validate_unit_eligibility(self.employee, self.leave_type)
            return super().validate_balance_leaves()

        # Preserve a meaningful standard value for HRMS overlap/max-day behavior.
        self.total_leave_days = sum(1 for row in result["details"] if flt(row["leave_hours"]) > 0)
        self.leave_balance = self.custom_hour_balance_before
        validate_hour_balance(self)

    def create_leave_ledger_entry(self, submit=True):
        if self.is_historical_migration():
            deduction = flt(self.custom_legacy_balance_deducted)
            if not deduction:
                deduction = (
                    flt(self.custom_leave_hours)
                    if self.custom_leave_unit == "Hours"
                    else flt(self.total_leave_days)
                )
            args = {
                "leaves": -abs(deduction),
                "from_date": self.from_date,
                "to_date": self.to_date,
                "is_lwp": frappe.db.get_value("Leave Type", self.leave_type, "is_lwp"),
                "holiday_list": get_holiday_list_for_employee(
                    self.employee, raise_exception=False
                ) or "",
            }
            if deduction or not submit:
                create_leave_ledger_entry(self, args, submit)
            return
        if get_leave_unit(self.leave_type) != "Hours":
            return super().create_leave_ledger_entry(submit)
        if self.status != "Approved" and submit:
            return
        args = {
            "leaves": flt(self.custom_leave_hours) * -1,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "is_lwp": frappe.db.get_value("Leave Type", self.leave_type, "is_lwp"),
            "holiday_list": get_holiday_list_for_employee(
                self.employee, raise_exception=not frappe.flags.in_patch
            ) or "",
        }
        create_leave_ledger_entry(self, args, submit)

    def update_attendance(self):
        if self.is_historical_migration():
            return
        if get_leave_unit(self.leave_type) == "Hours":
            return
        return super().update_attendance()

    def cancel_attendance(self):
        if self.is_historical_migration():
            return
        if get_leave_unit(self.leave_type) == "Hours":
            return
        return super().cancel_attendance()


def backfill_migrated_leave_ledgers():
    """Create missing ledger deductions for migrated applications imported before this fix."""
    applications = frappe.get_all(
        "Leave Application",
        filters={MIGRATED_RECORD_FIELD: 1, "status": "Approved", "docstatus": 1},
        pluck="name",
    )
    created = []
    for name in applications:
        if frappe.db.exists(
            "Leave Ledger Entry",
            {"transaction_type": "Leave Application", "transaction_name": name, "docstatus": 1},
        ):
            continue
        frappe.get_doc("Leave Application", name).create_leave_ledger_entry()
        created.append(name)
    return {"created": created, "count": len(created)}
