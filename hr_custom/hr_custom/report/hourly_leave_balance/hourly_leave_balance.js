frappe.query_reports["Hourly Leave Balance"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "leave_type", label: __("Leave Type"), fieldtype: "Link", options: "Leave Type", get_query: () => ({ filters: { custom_leave_unit: "Hours" } }) },
		{ fieldname: "as_of_date", label: __("As Of Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
	],
};
