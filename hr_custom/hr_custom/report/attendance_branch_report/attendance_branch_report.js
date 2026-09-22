frappe.query_reports["Attendance Branch Report"] = {
  filters: [
    {fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start(), reqd: 1},
    {fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1},
    {fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee"},
    {fieldname: "branch", label: __("Attendance Branch"), fieldtype: "Link", options: "Branch"},
    {fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nPresent\nAbsent\nOn Leave\nHalf Day\nWork From Home"}
  ]
};
