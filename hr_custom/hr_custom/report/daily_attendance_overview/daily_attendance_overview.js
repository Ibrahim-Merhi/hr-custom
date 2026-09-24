frappe.query_reports["Daily Attendance Overview"] = {
	filters: [
		{fieldname: "period_type", label: __("Period"), fieldtype: "Select", options: ["Day", "Week", "Month"], default: "Day", reqd: 1},
		{fieldname: "date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1},
		{fieldname: "attendance_status", label: __("Attendance Status"), fieldtype: "Select", options: ["All", "Present", "Absent"], default: "All", reqd: 1},
		{fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company"},
		{fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch"},
		{fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department"},
	],
};
