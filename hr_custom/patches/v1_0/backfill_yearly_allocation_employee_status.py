import frappe


def execute():
    frappe.db.sql(
        """
        update `tabYearly Leave Allocation Employee` allocation_employee
        inner join `tabEmployee` employee on employee.name = allocation_employee.employee
        set
            allocation_employee.employee_status = employee.status,
            allocation_employee.is_active = if(employee.status = 'Active', 1, 0),
            allocation_employee.exclude_from_allocation = if(
                employee.status = 'Active',
                allocation_employee.exclude_from_allocation,
                1
            )
        """
    )
