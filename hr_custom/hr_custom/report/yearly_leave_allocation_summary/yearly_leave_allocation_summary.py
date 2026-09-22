import frappe


def execute(filters=None):
    filters = frappe._dict(filters or {}); conditions = ["1=1"]; values = {}
    mapping = {"year":"y.allocation_year","company":"y.company","employee":"d.employee","department":"e.department","branch":"e.branch","employment_type":"e.employment_type","leave_type":"d.leave_type","leave_unit":"d.leave_unit"}
    for key, column in mapping.items():
        if filters.get(key): conditions.append(f"{column}=%({key})s"); values[key] = filters[key]
    data = frappe.db.sql(f"""select y.allocation_year, y.company, d.employee, e.employee_name, e.attendance_device_id, e.department, e.branch, e.employment_type, d.leave_type, d.leave_unit, d.allocated_amount, d.standard_leave_allocation, d.allocation_status from `tabYearly Leave Allocation Detail` d join `tabYearly Leave Allocation` y on y.name=d.parent left join `tabEmployee` e on e.name=d.employee where {' and '.join(conditions)} order by e.employee_name,d.leave_type""", values, as_dict=True)
    columns = [("allocation_year","Year","Int",None,70),("company","Company","Link","Company",120),("employee","Employee ID","Link","Employee",130),("employee_name","Employee Name","Data",None,170),("attendance_device_id","Attendance Device ID","Data",None,130),("department","Department","Link","Department",130),("branch","Branch","Link","Branch",100),("employment_type","Employment Type","Link","Employment Type",120),("leave_type","Leave Type","Link","Leave Type",150),("leave_unit","Unit","Data",None,70),("allocated_amount","Allocated Amount","Float",None,120),("standard_leave_allocation","Leave Allocation","Link","Leave Allocation",160),("allocation_status","Status","Data",None,100)]
    return [{"fieldname":f,"label":l,"fieldtype":t,"options":o,"width":w} for f,l,t,o,w in columns], data
