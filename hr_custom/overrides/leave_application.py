import frappe
from frappe.utils import flt
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry

from hr_custom.services.hourly_leave import apply_calculation, validate_hour_balance
from hr_custom.services.work_schedule import get_leave_unit, validate_unit_eligibility


class HourlyLeaveApplication(LeaveApplication):
    """Use HRMS unchanged for day leave and extend only hour-based Leave Types."""

    def validate_balance_leaves(self):
        result = apply_calculation(self)
        if result["leave_unit"] != "Hours":
            validate_unit_eligibility(self.employee, self.leave_type)
            return super().validate_balance_leaves()

        # Preserve a meaningful standard value for HRMS overlap/max-day behavior.
        self.total_leave_days = sum(1 for row in result["details"] if flt(row["leave_hours"]) > 0)
        self.leave_balance = self.custom_hour_balance_before
        validate_hour_balance(self)

    def create_leave_ledger_entry(self, submit=True):
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
        if get_leave_unit(self.leave_type) == "Hours":
            return
        return super().update_attendance()

    def cancel_attendance(self):
        if get_leave_unit(self.leave_type) == "Hours":
            return
        return super().cancel_attendance()
