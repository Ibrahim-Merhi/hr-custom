import frappe
from frappe import _
def execute(filters=None):
    f=frappe._dict(filters or {}); conditions=["date(c.time) between %(from_date)s and %(to_date)s"]; values={"from_date":f.from_date,"to_date":f.to_date}
    if f.employee: conditions.append("c.employee=%(employee)s"); values["employee"]=f.employee
    if f.branch: conditions.append("c.custom_branch=%(branch)s"); values["branch"]=f.branch
    data=frappe.db.sql(f"select c.employee,c.employee_name,c.time,c.log_type,c.custom_branch,c.custom_latitude,c.custom_longitude,c.custom_gps_accuracy,c.custom_distance_from_branch,c.custom_checkin_source,c.custom_device_info,c.custom_ip_address,c.custom_geofence_validated from `tabEmployee Checkin` c where {' and '.join(conditions)} order by c.time desc",values,as_dict=True)
    specs=[("employee","Employee","Link","Employee",120),("employee_name","Employee Name","Data",None,170),("time","Time","Datetime",None,160),("log_type","IN/OUT","Data",None,70),("custom_branch","Branch","Link","Branch",120),("custom_latitude","Latitude","Float",None,100),("custom_longitude","Longitude","Float",None,100),("custom_gps_accuracy","GPS Accuracy","Float",None,100),("custom_distance_from_branch","Distance","Float",None,90),("custom_checkin_source","Source","Data",None,100),("custom_device_info","Device","Data",None,140),("custom_ip_address","IP","Data",None,110),("custom_geofence_validated","Geofence Validated","Check",None,120)]
    return [{"fieldname":a,"label":_(b),"fieldtype":c,"options":d,"width":e} for a,b,c,d,e in specs],data
