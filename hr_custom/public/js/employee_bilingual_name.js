frappe.ui.form.on("Employee", {
	refresh(frm) {
		// Register the history render first.  Layout customisation must never be
		// allowed to prevent the read-only HR tables from loading.
		setTimeout(() => load_employee_hr_history(frm), 100);
		try {
			simplify_employee_form(frm);
			sync_arabic_full_name(frm);
		} catch (error) {
			console.error("Unable to customise the Employee form layout", error);
		}
	},
	custom_first_name_ar: sync_arabic_full_name,
	custom_middle_name_ar: sync_arabic_full_name,
	custom_last_name_ar: sync_arabic_full_name,
});

function sync_arabic_full_name(frm) {
	const fullName = [frm.doc.custom_first_name_ar, frm.doc.custom_middle_name_ar, frm.doc.custom_last_name_ar]
		.filter(Boolean).map(value => value.trim()).filter(Boolean).join(" ");
	if (fullName && frm.doc.custom_employee_name_ar !== fullName) frm.set_value("custom_employee_name_ar", fullName);
}

async function load_employee_hr_history(frm) {
	if (frm.is_new()) return;
	const leaveField = frm.fields_dict.custom_leave_balances_html;
	const attendanceField = frm.fields_dict.custom_attendance_log_html;
	if (!leaveField || !attendanceField) return;
	set_history_html(leaveField, `<div class="text-muted p-3">${__("Loading leave balances…")}</div>`);
	set_history_html(attendanceField, `<div class="text-muted p-3">${__("Loading attendance log…")}</div>`);
	try {
		const current = frappe.datetime.get_today();
		const selectedMonth = cint(frm.__hr_attendance_month) || cint(current.slice(5, 7));
		const selectedYear = cint(frm.__hr_attendance_year) || cint(current.slice(0, 4));
		const { message } = await frappe.call({
			method: "hr_custom.services.employee_profile.get_employee_hr_history",
			args: { employee: frm.doc.name, month: selectedMonth, year: selectedYear }
		});
		const leaveRows = (message.balances || []).map(row => {
			const used = flt(row.used);
			const usedValue = used > 0
				? `<a href="#" class="used-leaves-link" data-employee="${history_cell(frm.doc.name)}" data-leave-type="${history_cell(row.leave_type)}" data-from-date="${history_cell(row.from_date)}" data-to-date="${history_cell(row.to_date)}" title="${__("Open used leave applications")}">${history_cell(row.used)}</a>`
				: history_cell(row.used);
			return `<tr><td>${history_cell(row.leave_type)}</td><td>${history_cell(__(row.unit))}</td><td>${history_cell(row.allocated)}</td><td>${usedValue}</td><td class="text-success"><b>${history_cell(row.remaining)}</b></td><td>${history_cell(frappe.datetime.str_to_user(row.from_date))} – ${history_cell(frappe.datetime.str_to_user(row.to_date))}</td></tr>`;
		});
		set_history_html(leaveField, render_history_table(
			[__("Leave Type"), __("Unit"), __("Total Allocated Leaves"), __("Used Leaves"), __("Available Leaves"), __("Period")],
			leaveRows,
			__("No active leave allocations were found for this employee.")
		));
		bind_used_leave_links(leaveField);
		frm.__hr_attendance_month = cint(message.attendance_period?.month) || selectedMonth;
		frm.__hr_attendance_year = cint(message.attendance_period?.year) || selectedYear;
		frm.__hr_attendance_rows = message.attendance || [];
		set_history_html(attendanceField, render_attendance_section(frm));
		bind_attendance_log_actions(frm, attendanceField);
	} catch (error) {
		const failed = `<div class="text-danger p-3">${__("Unable to load HR history. Please refresh and try again.")}</div>`;
		set_history_html(leaveField, failed);
		set_history_html(attendanceField, failed);
	}
}

function render_attendance_section(frm) {
	const month = cint(frm.__hr_attendance_month);
	const year = cint(frm.__hr_attendance_year);
	const rows = frm.__hr_attendance_rows || [];
	const monthOptions = moment.months().map((label, index) => `<option value="${index + 1}" ${index + 1 === month ? "selected" : ""}>${history_cell(label)}</option>`).join("");
	const currentYear = cint(frappe.datetime.get_today().slice(0, 4));
	const startYear = Math.min(year, currentYear - 8);
	const endYear = Math.max(year, currentYear + 1);
	const yearOptions = Array.from({length: endYear - startYear + 1}, (_, index) => endYear - index)
		.map(value => `<option value="${value}" ${value === year ? "selected" : ""}>${value}</option>`).join("");
	const table = render_history_table(
		[__("Date"), __("Status"), __("Check In"), __("Check Out"), __("Hours"), __("Check-in Branch"), __("Check-out Branch")],
		rows.map(attendance_history_row),
		__("No attendance records were found for this employee in the selected month.")
	);
	return `<div class="hr-attendance-log">
		<div class="d-flex flex-wrap align-items-end gap-2 mb-3">
			<label class="mb-0"><span class="d-block text-muted small mb-1">${__("Month")}</span><select class="form-control hr-attendance-month" style="min-width:150px">${monthOptions}</select></label>
			<label class="mb-0"><span class="d-block text-muted small mb-1">${__("Year")}</span><select class="form-control hr-attendance-year" style="min-width:110px">${yearOptions}</select></label>
			<button type="button" class="btn btn-default hr-attendance-export">${__("Export CSV")}</button>
			<button type="button" class="btn btn-default hr-attendance-print">${__("Print / Save PDF")}</button>
			<span class="text-muted small ml-auto">${rows.length} ${__("record(s)")}</span>
		</div>${table}</div>`;
}

function attendance_history_row(row) {
	return `<tr><td><a href="/app/attendance/${encodeURIComponent(row.name)}">${history_cell(frappe.datetime.str_to_user(row.attendance_date))}</a></td><td>${history_cell(__(row.status))}</td><td>${history_cell(row.in_time ? frappe.datetime.str_to_user(row.in_time) : null)}</td><td>${history_cell(row.out_time ? frappe.datetime.str_to_user(row.out_time) : null)}</td><td>${history_cell(Number(row.working_hours || 0).toFixed(2))}</td><td>${history_cell(row.custom_check_in_branch)}</td><td>${history_cell(row.custom_check_out_branch)}</td></tr>`;
}

function bind_attendance_log_actions(frm, field) {
	const wrapper = field.$wrapper;
	wrapper.off("change.hr_custom_attendance_period");
	wrapper.on("change.hr_custom_attendance_period", ".hr-attendance-month,.hr-attendance-year", async function () {
		frm.__hr_attendance_month = cint(wrapper.find(".hr-attendance-month").val());
		frm.__hr_attendance_year = cint(wrapper.find(".hr-attendance-year").val());
		await load_employee_hr_history(frm);
	});
	wrapper.off("click.hr_custom_attendance_export").on("click.hr_custom_attendance_export", ".hr-attendance-export", () => export_attendance_csv(frm));
	wrapper.off("click.hr_custom_attendance_print").on("click.hr_custom_attendance_print", ".hr-attendance-print", () => print_attendance_log(frm));
}

function export_attendance_csv(frm) {
	const headers = [__("Date"), __("Status"), __("Check In"), __("Check Out"), __("Hours"), __("Check-in Branch"), __("Check-out Branch")];
	const values = (frm.__hr_attendance_rows || []).map(row => [row.attendance_date, __(row.status), row.in_time || "", row.out_time || "", Number(row.working_hours || 0).toFixed(2), row.custom_check_in_branch || "", row.custom_check_out_branch || ""]);
	const quote = value => `"${String(value ?? "").replaceAll('"', '""')}"`;
	const csv = [headers, ...values].map(row => row.map(quote).join(",")).join("\r\n");
	const link = document.createElement("a");
	link.href = URL.createObjectURL(new Blob(["\ufeff", csv], {type: "text/csv;charset=utf-8"}));
	link.download = `${frm.doc.name}-attendance-${frm.__hr_attendance_year}-${String(frm.__hr_attendance_month).padStart(2, "0")}.csv`;
	link.click();
	URL.revokeObjectURL(link.href);
}

function print_attendance_log(frm) {
	const rows = frm.__hr_attendance_rows || [];
	const title = `${__("Attendance Log")} — ${frm.doc.employee_name || frm.doc.name} — ${moment({year: frm.__hr_attendance_year, month: frm.__hr_attendance_month - 1}).format("MMMM YYYY")}`;
	const table = render_history_table(
		[__("Date"), __("Status"), __("Check In"), __("Check Out"), __("Hours"), __("Check-in Branch"), __("Check-out Branch")],
		rows.map(attendance_history_row),
		__("No attendance records were found for this employee in the selected month.")
	);
	const printWindow = window.open("", "_blank");
	if (!printWindow) return frappe.msgprint(__("Allow pop-ups to print or save this attendance report as PDF."));
	printWindow.opener = null;
	printWindow.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${history_cell(title)}</title><style>body{font-family:Arial,sans-serif;padding:24px;color:#172033}h1{font-size:20px;margin:0 0 18px}table{width:100%;border-collapse:collapse;font-size:11px}th,td{border:1px solid #ccd3dc;padding:7px;text-align:start}th{background:#f1f4f8}a{color:inherit;text-decoration:none}@page{size:landscape;margin:12mm}</style></head><body><h1>${history_cell(title)}</h1>${table}</body></html>`);
	printWindow.document.close();
	printWindow.focus();
	setTimeout(() => printWindow.print(), 250);
}

function bind_used_leave_links(field) {
	field.$wrapper.off("click.hr_custom_used_leave", ".used-leaves-link");
	field.$wrapper.on("click.hr_custom_used_leave", ".used-leaves-link", function (event) {
		event.preventDefault();
		const link = this.dataset;
		frappe.route_options = {
			employee: link.employee,
			leave_type: link.leaveType,
			status: "Approved",
			docstatus: 1,
			from_date: ["<=", link.toDate],
			to_date: [">=", link.fromDate],
		};
		frappe.set_route("List", "Leave Application");
	});
}

function set_history_html(field, html) {
	// HTML controls are refreshed when a collapsible section opens. Persisting
	// content in df.options prevents Frappe from replacing the table with an
	// empty value during that refresh.
	field.df.options = html;
	field.refresh();
}

function render_history_table(headers, rows, emptyMessage) {
	if (!rows.length) return `<div class="text-muted p-3">${emptyMessage}</div>`;
	return `<div class="table-responsive"><table class="table table-bordered table-hover">
		<thead><tr>${headers.map(value => `<th>${value}</th>`).join("")}</tr></thead>
		<tbody>${rows.join("")}</tbody></table></div>`;
}

function history_cell(value) {
	return frappe.utils.escape_html(value === null || value === undefined || value === "" ? "—" : String(value));
}

function simplify_employee_form(frm) {
	["salutation", "employment_details", "custom_default_mobile_leave_type", "custom_use_custom_work_schedule", "custom_weekly_working_hours"].forEach(fieldname => {
		if (frm.fields_dict[fieldname]) frm.set_df_property(fieldname, "hidden", 1);
	});
	const sectionField = frm.fields_dict.custom_personal_information_section;
	const section = sectionField?.$wrapper?.get(0) || sectionField?.wrapper;
	const body = section instanceof Element ? section.querySelector(".section-body") : null;
	if (!body) return;
	const columns = body.querySelectorAll(".form-column");
	["gender", "date_of_birth", "date_of_joining", "status"].forEach((fieldname, index) => {
		const wrapper = frm.fields_dict[fieldname]?.wrapper;
		const target = columns[index < 2 ? 0 : 1] || body;
		if (wrapper && wrapper.parentElement !== target) target.appendChild(wrapper);
	});
}
