frappe.query_reports["Daily Attendance Overview"] = {
	filters: [
		{fieldname: "period_type", label: __("Period"), fieldtype: "Select", options: ["Day", "Week", "Month"], default: "Day", reqd: 1},
		{fieldname: "date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1},
		{fieldname: "attendance_status", label: __("Status"), fieldtype: "Select", options: ["All", "Present", "Absent"], default: "All", reqd: 1},
		{fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company"},
		{fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch"},
		{fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department"},
	],
	onload(report) {
		const printButton = report.page.add_inner_button(__("Print"), () => {
			report.print_report({orientation: "Landscape"});
		});
		printButton.addClass("btn-primary").prepend('<span class="fa fa-print" style="margin-right:6px"></span>');
		if (!document.getElementById("daily-attendance-report-style")) {
			$("<style id='daily-attendance-report-style'>.query-report .dt-scrollable{border-radius:12px;border:1px solid var(--border-color)}.query-report .dt-header .dt-cell{background:var(--subtle-fg);font-weight:700}.query-report .dt-row:nth-child(even) .dt-cell{background:rgba(140,150,165,.045)}.attendance-status-pill{display:inline-flex;padding:3px 10px;border-radius:999px;font-weight:700;font-size:11px}.attendance-status-pill.present{background:#e3f6eb;color:#16834a}.attendance-status-pill.absent{background:#ffebed;color:#c73545}.attendance-person{font-weight:650;color:var(--text-color)}.attendance-duration{font-family:monospace;font-weight:700}</style>").appendTo("head");
		}
	},
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		if (column.fieldname === "status") {
			const status = String(data.status || "");
			const css = status.toLowerCase() === "present" || status === "حاضر" ? "present" : status.toLowerCase() === "absent" || status === "غائب" ? "absent" : "";
			return `<span class="attendance-status-pill ${css}">${frappe.utils.escape_html(formatted)}</span>`;
		}
		if (column.fieldname === "employee_name") return `<span class="attendance-person">${formatted}</span>`;
		if (column.fieldname === "working_hours") return `<span class="attendance-duration">${formatted}</span>`;
		return formatted;
	},
};
