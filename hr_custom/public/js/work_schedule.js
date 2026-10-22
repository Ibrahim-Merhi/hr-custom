const HR_CUSTOM_DAYS = [
	"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
];

function add_missing_schedule_days(frm) {
	const fieldname = "custom_weekly_working_hours";
	const existing = new Set((frm.doc[fieldname] || []).map((row) => row.day_of_week));
	HR_CUSTOM_DAYS.forEach((day, index) => {
		if (!existing.has(day)) {
			const row = frm.add_child(fieldname);
			row.day_of_week = day;
			row.working_hours = 0;
			row.sequence = index + 1;
			row.enabled = 1;
		}
	});
	frm.refresh_field(fieldname);
}

async function employee_leave_mode(frm) {
	if (frm.doc.custom_leave_calculation_mode_override) {
		return frm.doc.custom_leave_calculation_mode_override;
	}
	if (!frm.doc.employment_type) return "Days";
	const result = await frappe.db.get_value(
		"Employment Type",
		frm.doc.employment_type,
		["custom_leave_calculation_mode", "custom_weekly_work_schedule"],
	);
	return result.message?.custom_leave_calculation_mode || "Days";
}

async function copy_schedule_rows(frm, scheduleName) {
	if (!scheduleName) return false;
	const schedule = await frappe.db.get_doc("Weekly Work Schedule", scheduleName);
	frm.clear_table("custom_weekly_working_hours");
	(schedule.working_hours || []).forEach((source) => {
		const row = frm.add_child("custom_weekly_working_hours");
		["day_of_week", "working_hours", "from_time", "to_time", "sequence", "enabled"]
			.forEach((field) => row[field] = source[field]);
	});
	frm.refresh_field("custom_weekly_working_hours");
	return Boolean((schedule.working_hours || []).length);
}

async function configure_employee_schedule(frm, initialize = false) {
	const mode = await employee_leave_mode(frm);
	const hourly = ["Hours", "Both"].includes(mode);
	frm.toggle_display("custom_work_schedule_section", hourly);
	frm.toggle_display("custom_weekly_work_schedule", hourly);
	frm.toggle_display("custom_use_custom_work_schedule", hourly);
	frm.toggle_display("custom_weekly_working_hours", hourly && Boolean(frm.doc.custom_use_custom_work_schedule));
	if (!hourly || !initialize || frm.doc.custom_use_custom_work_schedule) return;

	await frm.set_value("custom_use_custom_work_schedule", 1);
	let copied = false;
	if (frm.doc.custom_weekly_work_schedule) {
		copied = await copy_schedule_rows(frm, frm.doc.custom_weekly_work_schedule);
	} else if (frm.doc.employment_type) {
		const type = await frappe.db.get_value(
			"Employment Type",
			frm.doc.employment_type,
			"custom_weekly_work_schedule",
		);
		if (type.message?.custom_weekly_work_schedule) {
			copied = await copy_schedule_rows(frm, type.message.custom_weekly_work_schedule);
		}
	}
	if (!copied) add_missing_schedule_days(frm);
	frm.toggle_display("custom_weekly_working_hours", true);
	frm.scroll_to_field("custom_work_schedule_section");
}

frappe.ui.form.on("Employment Type", {
	refresh(frm) {
		if (["Hours", "Both"].includes(frm.doc.custom_leave_calculation_mode)) {
			frm.add_custom_button(__("Complete Weekly Schedule"), () => add_missing_schedule_days(frm));
		}
	},
	custom_leave_calculation_mode(frm) {
		frm.toggle_display("custom_weekly_working_hours", ["Hours", "Both"].includes(frm.doc.custom_leave_calculation_mode));
	},
});

frappe.ui.form.on("Employee", {
	async refresh(frm) {
		const can_manage_location_bypass =
			frappe.session.user === "Administrator" || frappe.user.has_role("System Manager");
		frm.toggle_display("custom_location_not_required", can_manage_location_bypass);

		if (frm.doc.custom_use_custom_work_schedule) {
			frm.add_custom_button(__("Complete Weekly Schedule"), () => add_missing_schedule_days(frm));
		}
		if (frm.doc.custom_weekly_work_schedule && !frm.doc.custom_use_custom_work_schedule) {
			frm.add_custom_button(__("Copy Schedule for Adjustment"), async () => {
				frm.set_value("custom_use_custom_work_schedule", 1);
				await copy_schedule_rows(frm, frm.doc.custom_weekly_work_schedule);
			}, __("Schedule"));
		}
		await configure_employee_schedule(frm);
	},
	async employment_type(frm) {
		await configure_employee_schedule(frm, true);
	},
	async custom_leave_calculation_mode_override(frm) {
		await configure_employee_schedule(frm, true);
	},
	custom_use_custom_work_schedule(frm) {
		frm.toggle_display("custom_weekly_working_hours", Boolean(frm.doc.custom_use_custom_work_schedule));
		if (frm.doc.custom_use_custom_work_schedule && !(frm.doc.custom_weekly_working_hours || []).length) {
			add_missing_schedule_days(frm);
		}
	},
});
