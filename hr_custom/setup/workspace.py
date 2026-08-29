import json
import frappe
PREFIX="hr_custom_"
LABELS={"Mobile Attendance","Attendance Correction Request","Attendance Exception","HR Attendance Dashboard","HR Mobile Attendance Settings","Employee Attendance Device","Daily Attendance Overview","Mobile Checkin Audit","Attendance Exceptions"}
ITEMS=[("Mobile Attendance","URL","/attendance"),("HR Attendance Dashboard","Page","hr-attendance-dashboard"),("Attendance Correction Request","DocType","Attendance Correction Request"),("Attendance Exception","DocType","Attendance Exception"),("HR Mobile Attendance Settings","DocType","HR Mobile Attendance Settings"),("Employee Attendance Device","DocType","Employee Attendance Device"),("Daily Attendance Overview","Report","Daily Attendance Overview"),("Mobile Checkin Audit","Report","Mobile Checkin Audit"),("Attendance Exceptions","Report","Attendance Exceptions")]
def ensure_hr_workspace_section():
    if not frappe.db.exists("Workspace","HR"): return
    doc=frappe.get_doc("Workspace","HR"); content=[x for x in json.loads(doc.content or "[]") if not x.get("id","").startswith(PREFIX)]
    content.append({"id":"hr_custom_header","type":"header","data":{"text":'<span class="h4"><b>Custom HRMS</b></span>',"col":12}})
    for i,(label,kind,target) in enumerate(ITEMS): content.append({"id":f"hr_custom_{i}","type":"shortcut","data":{"shortcut_name":label,"col":4}})
    doc.content=json.dumps(content,separators=(",",":")); doc.set("shortcuts",[r.as_dict() for r in doc.shortcuts if r.label not in LABELS])
    for label,kind,target in ITEMS:
        row={"type":kind,"label":label,"color":"Green" if label=="Mobile Attendance" else "Grey"}
        if kind=="URL": row["url"]=target
        else: row["link_to"]=target
        if kind=="DocType": row["doc_view"]="List"
        doc.append("shortcuts",row)
    _save(doc)
def remove_hr_workspace_section():
    if not frappe.db.exists("Workspace","HR"): return
    doc=frappe.get_doc("Workspace","HR"); doc.content=json.dumps([x for x in json.loads(doc.content or "[]") if not x.get("id","").startswith(PREFIX)],separators=(",",":")); doc.set("shortcuts",[r.as_dict() for r in doc.shortcuts if r.label not in LABELS]); _save(doc)
def _save(doc):
    for i,row in enumerate(doc.shortcuts,1): row.idx=i
    doc.flags.ignore_permissions=True; mode=frappe.conf.developer_mode
    try: frappe.conf.developer_mode=0; doc.save()
    finally: frappe.conf.developer_mode=mode
    frappe.clear_cache(doctype="Workspace")
