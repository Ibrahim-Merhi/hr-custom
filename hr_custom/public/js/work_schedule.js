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
	refresh(frm) {
		if (frm.doc.custom_use_custom_work_schedule) {
			frm.add_custom_button(__("Complete Weekly Schedule"), () => add_missing_schedule_days(frm));
		}
		if (frm.doc.custom_weekly_work_schedule && !frm.doc.custom_use_custom_work_schedule) {
			frm.add_custom_button(__("Copy Schedule for Adjustment"), async () => {
				const schedule = await frappe.db.get_doc("Weekly Work Schedule", frm.doc.custom_weekly_work_schedule);
				frm.set_value("custom_use_custom_work_schedule", 1);
				frm.clear_table("custom_weekly_working_hours");
				(schedule.working_hours || []).forEach(source => {
					const row = frm.add_child("custom_weekly_working_hours");
					["day_of_week", "working_hours", "from_time", "to_time", "sequence", "enabled"].forEach(field => row[field] = source[field]);
				});
				frm.refresh_field("custom_weekly_working_hours");
			}, __("Schedule"));
		}
	},
	custom_use_custom_work_schedule(frm) {
		frm.toggle_display("custom_weekly_working_hours", Boolean(frm.doc.custom_use_custom_work_schedule));
	},
});
