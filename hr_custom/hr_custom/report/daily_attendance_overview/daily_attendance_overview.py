import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    date = getdate(filters.date)
    conditions, values = ["a.attendance_date=%(date)s", "a.docstatus<2"], {"date": date}
    for field in ("company", "department", "shift", "employee", "status"):
        if filters.get(field): conditions.append(f"a.{field}=%({field})s"); values[field] = filters[field]
    if filters.branch: conditions.append("e.branch=%(branch)s"); values["branch"] = filters.branch
    data = frappe.db.sql(f"""select a.employee,a.employee_name,e.branch,a.department,a.shift,a.in_time,a.out_time,a.working_hours,a.late_entry,a.early_exit,a.status from `tabAttendance` a left join `tabEmployee` e on e.name=a.employee where {' and '.join(conditions)} order by e.branch,a.employee_name""", values, as_dict=True)
    for row in data:
        audit = frappe.db.get_value("Employee Checkin", {"employee": row.employee, "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]}, ["custom_minutes_late", "custom_minutes_early"], order_by="time asc", as_dict=True) or {}
        row.update(minutes_late=audit.get("custom_minutes_late", 0), minutes_early=audit.get("custom_minutes_early", 0))
        row.exception = frappe.db.exists("Attendance Exception", {"employee": row.employee, "attendance_date": date, "status": "Open"})
    return _columns(), data


def _columns():
    return [{"fieldname":f,"label":_(l),"fieldtype":t,"options":o,"width":w} for f,l,t,o,w in [("employee","Employee","Link","Employee",120),("employee_name","Employee Name","Data",None,180),("branch","Branch","Link","Branch",120),("department","Department","Link","Department",140),("shift","Shift","Link","Shift Type",110),("in_time","First IN","Datetime",None,150),("out_time","Last OUT","Datetime",None,150),("working_hours","Working Hours","Float",None,110),("late_entry","Late","Check",None,70),("minutes_late","Minutes Late","Int",None,100),("early_exit","Early Exit","Check",None,80),("minutes_early","Minutes Early","Int",None,100),("status","Attendance Status","Data",None,120),("exception","Exception","Link","Attendance Exception",130)]]
