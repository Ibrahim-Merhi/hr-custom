const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

frappe.ui.form.on("Weekly Work Schedule", {
	refresh(frm) {
		frm.add_custom_button(__("Complete Week"), () => {
			const present = new Set((frm.doc.working_hours || []).map(row => row.day_of_week));
			DAYS.forEach((day, index) => {
				if (!present.has(day)) {
					const row = frm.add_child("working_hours");
					Object.assign(row, {day_of_week: day, working_hours: 0, sequence: index + 1, enabled: 1});
				}
			});
			frm.refresh_field("working_hours");
		}, __("Schedule"));
		if (!frm.is_new()) {
			frm.add_custom_button(__("Assign Employees"), () => {
				const dialog = new frappe.ui.form.MultiSelectDialog({
					doctype: "Employee", target: frm, add_filters_group: 1,
					setters: {company: frm.doc.company || null, department: null, status: "Active"},
					get_query: () => ({filters: {status: "Active", ...(frm.doc.company ? {company: frm.doc.company} : {})}}),
					action(selections) {
						frappe.call({
							method: "hr_custom.hr_custom.doctype.weekly_work_schedule.weekly_work_schedule.assign_employees",
							args: {schedule: frm.doc.name, employees: selections},
							freeze: true,
						}).then(({message}) => {
							dialog.dialog.hide();
							frappe.show_alert({message: __("Schedule assigned to {0} employee(s).", [message.assigned]), indicator: "green"});
						});
					}
				});
			}, __("Schedule"));
			frm.add_custom_button(__("View Assigned Employees"), () => {
				frappe.set_route("List", "Employee", {custom_weekly_work_schedule: frm.doc.name});
			}, __("Schedule"));
		}
	}
});
