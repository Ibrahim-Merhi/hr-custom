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
		const { message } = await frappe.call({
			method: "hr_custom.services.employee_profile.get_employee_hr_history",
			args: { employee: frm.doc.name }
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
		set_history_html(attendanceField, render_history_table(
			[__("Date"), __("Status"), __("Check In"), __("Check Out"), __("Hours"), __("Check-in Branch"), __("Check-out Branch")],
			(message.attendance || []).map(row => `<tr><td><a href="/app/attendance/${encodeURIComponent(row.name)}">${history_cell(frappe.datetime.str_to_user(row.attendance_date))}</a></td><td>${history_cell(__(row.status))}</td><td>${history_cell(row.in_time ? frappe.datetime.str_to_user(row.in_time) : null)}</td><td>${history_cell(row.out_time ? frappe.datetime.str_to_user(row.out_time) : null)}</td><td>${history_cell(Number(row.working_hours || 0).toFixed(2))}</td><td>${history_cell(row.custom_check_in_branch)}</td><td>${history_cell(row.custom_check_out_branch)}</td></tr>`),
			__("No attendance records were found for this employee.")
		));
	} catch (error) {
		const failed = `<div class="text-danger p-3">${__("Unable to load HR history. Please refresh and try again.")}</div>`;
		set_history_html(leaveField, failed);
		set_history_html(attendanceField, failed);
	}
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
