frappe.query_reports["Weekly Employee Hours"] = {
	filters: [
		{fieldname: "week_start", label: __("Week Starting"), fieldtype: "Date", reqd: 1,
		 default: frappe.datetime.add_days(frappe.datetime.get_today(), -((new Date().getDay() + 6) % 7))},
		{fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company"},
		{fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department"},
		{fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee"},
		{fieldname: "show_only_exceptions", label: __("Only Missing/Variance"), fieldtype: "Check", default: 0}
	]
};
