frappe.query_reports["Yearly Leave Allocation Summary"] = {filters:[
 {fieldname:"year",label:__("Year"),fieldtype:"Int"},{fieldname:"company",label:__("Company"),fieldtype:"Link",options:"Company"},
 {fieldname:"employee",label:__("Employee"),fieldtype:"Link",options:"Employee"},{fieldname:"department",label:__("Department"),fieldtype:"Link",options:"Department"},
 {fieldname:"branch",label:__("Branch"),fieldtype:"Link",options:"Branch"},{fieldname:"employment_type",label:__("Employment Type"),fieldtype:"Link",options:"Employment Type"},
 {fieldname:"leave_type",label:__("Leave Type"),fieldtype:"Link",options:"Leave Type"},{fieldname:"leave_unit",label:__("Unit"),fieldtype:"Select",options:"\nDays\nHours"}
]};
