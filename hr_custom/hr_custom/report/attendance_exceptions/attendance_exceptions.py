import frappe
from frappe import _


def execute(filters=None):
    f=frappe._dict(filters or {})
    conditions=["attendance_date between %(from_date)s and %(to_date)s"]
    values={"from_date":f.from_date,"to_date":f.to_date}
    for key in ("employee","branch","status"):
        if f.get(key): conditions.append(f"{key}=%({key})s"); values[key]=f[key]
    data=frappe.db.sql(f"select name,employee,attendance_date,exception_type,branch,shift_type,status,working_hours from `tabAttendance Exception` where {' and '.join(conditions)} order by attendance_date desc",values,as_dict=True)
    specs=[("name","Exception","Link","Attendance Exception",140),("employee","Employee","Link","Employee",120),("attendance_date","Date","Date",None,100),("exception_type","Exception","Data",None,150),("branch","Branch","Link","Branch",120),("shift_type","Shift","Link","Shift Type",120),("working_hours","Working Hours","Float",None,110),("status","Status","Data",None,90)]
    return [{"fieldname":a,"label":_(b),"fieldtype":c,"options":d,"width":e} for a,b,c,d,e in specs],data
