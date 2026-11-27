frappe.ui.form.on("Leave Application", {
	refresh(frm) {
		apply_leave_form_ui(frm);
		if (frm.is_new() && frm.doc.employee) apply_employee_defaults(frm);
		set_hourly_visibility(frm);
		if (frm.is_new()) {
			frm.add_custom_button(__("Request Mixed Leave"), () => request_mixed_leave(frm));
		}
		if (frm.doc.custom_split_leave_plan) {
			const periods = JSON.parse(frm.doc.custom_split_leave_plan);
			frm.dashboard.add_comment(periods.map(period => frappe.utils.escape_html(
				`${period.leave_type}: ${frappe.datetime.str_to_user(period.from_date)} – ${frappe.datetime.str_to_user(period.to_date)}`
			)).join("<br>"), "blue");
		}
		if (is_migrated_record(frm)) {
			setup_leave_approval_actions(frm);
			return;
		}
		if (frm.doc.leave_type) refresh_leave_unit(frm);
		setup_leave_approval_actions(frm);
		if (!frm.doc.custom_split_leave_plan && !frm.doc.custom_split_leave_parent &&
			frm.doc.docstatus === 1 && frm.doc.status === "Approved" &&
			(frappe.session.user === "Administrator" || frappe.user.has_role("HR Manager"))) {
			frm.add_custom_button(__("Modify Leave"), () => modify_approved_leave(frm));
		}
	},
	employee(frm) {
		apply_employee_defaults(frm);
		schedule_hourly_preview(frm);
	},
	leave_type(frm) {
		if (is_migrated_record(frm)) {
			set_hourly_visibility(frm);
			return;
		}
		refresh_leave_unit(frm);
	},
	from_date: schedule_hourly_preview,
	to_date: schedule_hourly_preview,
	custom_leave_duration: schedule_hourly_preview,
	custom_partial_hours: schedule_hourly_preview,
});

function request_mixed_leave(frm) {
	if (!frm.doc.employee) {
		frappe.msgprint(__("Select an employee first."));
		return;
	}
	frappe.prompt([
		{fieldname: "leave_type", label: __("First Leave Type"), fieldtype: "Link", options: "Leave Type", default: frm.doc.leave_type, reqd: 1},
		{fieldname: "from_date", label: __("First Period Starts"), fieldtype: "Date", default: frm.doc.from_date, reqd: 1},
		{fieldname: "additional_periods", label: __("Additional Leave Periods"), fieldtype: "Table", reqd: 1, fields: [
			{fieldname: "leave_type", label: __("Leave Type"), fieldtype: "Link", options: "Leave Type", reqd: 1, in_list_view: 1},
			{fieldname: "from_date", label: __("Period Starts"), fieldtype: "Date", reqd: 1, in_list_view: 1},
		]},
		{fieldname: "to_date", label: __("Final Date"), fieldtype: "Date", default: frm.doc.to_date, reqd: 1},
		{fieldname: "reason", label: __("Leave Reason"), fieldtype: "Small Text", default: frm.doc.description},
	], async values => {
		const {message} = await frappe.call({
			method: "hr_custom.services.simple_leave.submit_split_leave",
			type: "POST", args: {...values, additional_periods: JSON.stringify(values.additional_periods), employee: frm.doc.employee}, freeze: true,
		});
		frappe.set_route("Form", "Leave Application", message.name);
	}, __("Request Mixed Leave"), __("Send for Approval"));
}

function modify_approved_leave(frm) {
	frappe.prompt([
		{fieldname: "leave_type", label: __("Leave Type"), fieldtype: "Link", options: "Leave Type", default: frm.doc.leave_type, reqd: 1},
		{fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frm.doc.from_date, reqd: 1},
		{fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frm.doc.to_date, reqd: 1},
		{fieldname: "half_day", label: __("Half Day (day-based leave only)"), fieldtype: "Check", default: frm.doc.half_day},
		{fieldname: "half_day_date", label: __("Half Day Date"), fieldtype: "Date", default: frm.doc.half_day_date, depends_on: "eval:doc.half_day"},
		{fieldname: "leave_duration", label: __("Hourly Leave Duration"), fieldtype: "Select", options: ["Full Scheduled Hours", "Partial Hours"], default: frm.doc.custom_leave_duration || "Full Scheduled Hours"},
		{fieldname: "partial_hours", label: __("Requested Hours"), fieldtype: "Float", default: frm.doc.custom_partial_hours, depends_on: "eval:doc.leave_duration === 'Partial Hours'"},
		{fieldname: "reason", label: __("Leave Reason"), fieldtype: "Small Text", default: frm.doc.description},
		{fieldname: "amendment_note", label: __("Reason for Modification"), fieldtype: "Small Text", reqd: 1},
	], values => frappe.confirm(__("Replace the approved leave with this revised request? The original will be kept as a cancelled record."), async () => {
		const {message} = await frappe.call({
			method: "hr_custom.services.simple_leave.amend_approved_leave",
			type: "POST", args: {name: frm.doc.name, ...values}, freeze: true,
		});
		frappe.set_route("Form", "Leave Application", message.name);
	}), __("Modify Approved Leave"), __("Review Changes"));
}

function apply_leave_form_ui(frm) {
	frm.toggle_display("custom_legacy_leave_section", false);
	frm.toggle_display("sb_other_details", false);
	frm.toggle_display("leave_approver", false);
	frm.toggle_display("leave_approver_name", false);
	frm.toggle_display("follow_via_email", false);
	frm.set_df_property("company", "read_only", 1);
	frm.set_df_property("leave_approver", "read_only", 1);
}

function apply_employee_defaults(frm) {
	if (!frm.doc.employee || frm.doc.docstatus !== 0) return;
	frappe.call({
		method: "hr_custom.services.simple_leave.get_leave_application_employee_defaults",
		args: {employee: frm.doc.employee},
		callback(response) {
			const defaults = response.message || {};
			if (defaults.company) frm.set_value("company", defaults.company);
			if (defaults.leave_approver) frm.set_value("leave_approver", defaults.leave_approver);
		},
	});
}

function is_migrated_record(frm) {
	return Number(frm.doc.custom_is_migrated_record || 0) === 1;
}

function setup_leave_approval_actions(frm) {
	if (frm.is_new()) return;
	if (["Pending Approver Approval", "Pending HR Approval"].includes(frm.doc.custom_approval_stage)) {
		// A pending request must advance through the configured reviewers; the
		// standard Submit action would fail because HRMS only submits final states.
		frm.page.clear_primary_action();
	}
	frappe.call({
		method: "hr_custom.services.simple_leave.get_leave_approval_context",
		args: {name: frm.doc.name},
		callback(response) {
			const context = response.message || {};
			if (["Pending Approver Approval", "Pending HR Approval"].includes(context.stage)) {
				frm.page.clear_primary_action();
			}
			if (!context.can_act) return;
			frm.add_custom_button(__(context.is_final_hr_step ? "Final Approve & Submit" : "Approve"), () => run_leave_action(frm, "approve"), __("Approval"));
			frm.add_custom_button(__("Reject"), () => run_leave_action(frm, "reject"), __("Approval"));
		},
	});
}

function run_leave_action(frm, action) {
	frappe.prompt(
		[{fieldname: "remarks", label: __("Remarks"), fieldtype: "Small Text"}],
		(values) => frappe.call({
			method: "hr_custom.services.simple_leave.process_leave_approval",
			type: "POST",
			args: {name: frm.doc.name, action, remarks: values.remarks},
			freeze: true,
			freeze_message: action === "approve" ? __("Approving leave request…") : __("Rejecting leave request…"),
			callback: () => frm.reload_doc(),
		}),
		__(action === "approve" ? "Approve Leave Request" : "Reject Leave Request"),
		__(action === "approve" ? "Approve" : "Reject")
	);
}

function refresh_leave_unit(frm) {
	if (!frm.doc.leave_type) {
		frm.set_value("custom_leave_unit", "");
		set_hourly_visibility(frm);
		return;
	}
	frappe.db.get_value("Leave Type", frm.doc.leave_type, "custom_leave_unit").then((result) => {
		const unit = result.message.custom_leave_unit || "Days";
		frm.set_value("custom_leave_unit", unit);
		if (unit === "Hours" && !frm.doc.custom_leave_duration) {
			frm.set_value("custom_leave_duration", "Full Scheduled Hours");
		}
		set_hourly_visibility(frm);
		schedule_hourly_preview(frm);
	});
}

function set_hourly_visibility(frm) {
	const hourly = frm.doc.custom_leave_unit === "Hours";
	frm.toggle_display("half_day", !hourly);
	frm.toggle_display("half_day_date", !hourly);
	frm.toggle_display("total_leave_days", !hourly);
	frm.set_df_property("total_leave_days", "description", hourly ? __("Eligible scheduled dates; balance is deducted in hours.") : "");
}

const run_hourly_preview = frappe.utils.debounce((frm) => {
	if (
		is_migrated_record(frm) ||
		frm.doc.custom_leave_unit !== "Hours" ||
		![frm.doc.employee, frm.doc.leave_type, frm.doc.from_date, frm.doc.to_date].every(Boolean)
	) return;
	frappe.call({
		method: "hr_custom.api.hourly_leave.get_hourly_leave_preview",
		args: {
			employee: frm.doc.employee,
			leave_type: frm.doc.leave_type,
			from_date: frm.doc.from_date,
			to_date: frm.doc.to_date,
			leave_duration: frm.doc.custom_leave_duration,
			partial_hours: frm.doc.custom_partial_hours,
		},
		callback(response) {
			const data = response.message;
			if (!data) return;
			frm.set_value("custom_scheduled_hours", data.total_scheduled_hours);
			frm.set_value("custom_leave_hours", data.total_leave_hours);
			frm.set_value("custom_hour_balance_before", data.balance.remaining_hours);
			frm.set_value("custom_hour_balance_after", data.balance_after_leave);
			frm.clear_table("custom_leave_hour_details");
			(data.details || []).forEach((detail) => frm.add_child("custom_leave_hour_details", detail));
			frm.refresh_field("custom_leave_hour_details");
		},
	});
}, 350);

function schedule_hourly_preview(frm) {
	run_hourly_preview(frm);
}
