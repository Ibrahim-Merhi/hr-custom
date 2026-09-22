frappe.query_reports["Abnormal Attendance Records"] = {
	filters: [
		{fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start(), reqd: 1},
		{fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1},
		{fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee"},
		{fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch"},
		{fieldname: "exception_type", label: __("Abnormal Type"), fieldtype: "Select", options: "\nMissing Check Out\nMissing Check In\nDuplicate IN\nDuplicate OUT\nOutside Shift Window\nPoor GPS Accuracy\nOutside Geofence\nNo Shift Assigned\nNo Branch Assigned\nAttendance Conflict\nLeave Conflict\nOther"},
		{fieldname: "status", label: __("Resolution Status"), fieldtype: "Select", options: "\nOpen\nResolved", default: "Open"},
	],
	onload(report) {
		report.page.add_inner_button(__("Scan Recent Attendance"), () => frappe.call({
			method: "hr_custom.api.attendance_correction_workflow.scan_abnormal_attendance",
			args: {days: 31},
			freeze: true,
			freeze_message: __("Checking attendance records…"),
			callback: () => report.refresh(),
		}));
	},
};
