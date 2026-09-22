from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation

from hr_custom.services.work_schedule import get_leave_unit, validate_unit_eligibility


class HourlyLeaveAllocation(LeaveAllocation):
    """Allow standard Leave Allocation quantities to represent hours."""

    def validate(self):
        validate_unit_eligibility(self.employee, self.leave_type)
        return super().validate()

    def validate_leave_allocation_days(self):
        if get_leave_unit(self.leave_type) == "Hours":
            return
        return super().validate_leave_allocation_days()
