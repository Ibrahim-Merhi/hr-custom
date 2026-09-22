frappe.ui.form.on("Leave Application", {
	refresh(frm) {
		set_hourly_visibility(frm);
		if (frm.doc.leave_type) refresh_leave_unit(frm);
		setup_leave_approval_actions(frm);
	},
	employee: schedule_hourly_preview,
	leave_type(frm) {
		refresh_leave_unit(frm);
	},
	from_date: schedule_hourly_preview,
	to_date: schedule_hourly_preview,
	custom_leave_duration: schedule_hourly_preview,
	custom_partial_hours: schedule_hourly_preview,
});

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
	frm.set_df_property("total_leave_days", "description", hourly ? __("Eligible scheduled dates; balance is deducted in hours.") : "");
}

const run_hourly_preview = frappe.utils.debounce((frm) => {
	if (
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
