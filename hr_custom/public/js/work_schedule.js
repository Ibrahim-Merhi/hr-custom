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
	["custom_weekly_work_schedule", "custom_use_custom_work_schedule", "custom_weekly_working_hours"]
		.forEach((fieldname) => frm.toggle_display(fieldname, false));
	if (hourly && !frm.is_new()) await render_work_schedule_workspace(frm);
	if (hourly && initialize) frm.scroll_to_field("custom_work_schedule_section");
}

function schedule_time(value) {
	if (!value) return null;
	const parts = String(value).split(":").map(Number);
	return (parts[0] || 0) * 60 + (parts[1] || 0);
}

function end_time(fromTime, hours) {
	const start = schedule_time(fromTime);
	if (start === null || !Number(hours)) return null;
	const total = (start + Math.round(Number(hours) * 60)) % (24 * 60);
	return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}:00`;
}

function schedule_table_fields() {
	const updateEnd = function () {
		const row = this.grid_row?.doc;
		if (!row?.from_time || !Number(row.working_hours)) return;
		this.grid_row.on_grid_fields_dict.to_time.set_value(
			end_time(row.from_time, row.working_hours),
		);
	};
	return [
		{fieldname:"day_of_week",label:__("Day"),fieldtype:"Select",options:HR_CUSTOM_DAYS.join("\n"),reqd:1,in_list_view:1,columns:2},
		{fieldname:"working_hours",label:__("Working Hours"),fieldtype:"Float",precision:2,reqd:1,in_list_view:1,columns:2,onchange:updateEnd},
		{fieldname:"from_time",label:__("From Time"),fieldtype:"Time",in_list_view:1,columns:2,onchange:updateEnd},
		{fieldname:"to_time",label:__("To Time"),fieldtype:"Time",in_list_view:1,columns:2},
		{fieldname:"enabled",label:__("Enabled"),fieldtype:"Check",default:1,in_list_view:1,columns:1},
	];
}

async function render_work_schedule_workspace(frm) {
	if (!document.getElementById("employee-work-schedule-style")) {
		$("<style id='employee-work-schedule-style'>.schedule-workspace{overflow:hidden;border:1px solid var(--border-color);border-radius:12px}.schedule-tabs{display:grid;grid-template-columns:1fr 1fr;padding:5px;background:var(--subtle-fg);border-bottom:1px solid var(--border-color)}.schedule-tabs button{padding:10px;border:0;border-radius:8px;background:transparent;font-weight:600}.schedule-tabs button.active{background:var(--card-bg);box-shadow:0 1px 4px #0002}.schedule-panel{padding:18px}.schedule-revision{padding:14px;border:1px solid var(--border-color);border-radius:10px;margin-bottom:10px}.schedule-revision-summary{display:flex;justify-content:space-between;gap:15px}.schedule-revision-summary div,.schedule-revision span,.schedule-revision small{display:block}.schedule-revision span,.schedule-revision small{margin-top:4px;color:var(--text-muted)}.schedule-revision details{margin-top:12px}.schedule-revision summary{cursor:pointer;font-weight:600}.schedule-revision table{margin:10px 0 0}@media(max-width:600px){.schedule-revision-summary{flex-direction:column}}</style>").appendTo("head");
	}
	const field = frm.get_field("custom_work_schedule_workspace");
	if (!field) return;
	field.$wrapper.html(`<div class="text-muted p-3">${__("Loading work schedule...")}</div>`);
	try {
		const data = (await frappe.call("hr_custom.services.work_schedule_profile.get_profile", {employee:frm.doc.name})).message;
		const rows = data.rows || [];
		const currentRows = rows.length ? rows.map((row) => `<tr><td>${__(row.day_of_week)}</td><td>${Number(row.working_hours||0).toFixed(2)}</td><td>${row.from_time||"—"}</td><td>${row.to_time||"—"}</td></tr>`).join("") : `<tr><td colspan="4" class="text-muted">${__("No employee work schedule has been created.")}</td></tr>`;
		const history = (data.revisions || []).map((revision) => {
			const snapshot = (revision.schedule || []).map((row) => `<tr><td>${__(row.day_of_week)}</td><td>${Number(row.working_hours||0).toFixed(2)}</td><td>${row.from_time||"—"}</td><td>${row.to_time||"—"}</td></tr>`).join("");
			return `<article class="schedule-revision"><div class="schedule-revision-summary"><div><strong>${__("Revision")} #${revision.revision_number}</strong><span>${frappe.datetime.str_to_user(revision.effective_from)} – ${revision.effective_to ? frappe.datetime.str_to_user(revision.effective_to) : __("Current")}</span></div><div><b>${Number(revision.total_weekly_hours||0).toFixed(2)} ${__("hours per week")}</b><small>${frappe.utils.escape_html(revision.change_summary||"")} · ${frappe.utils.escape_html(revision.changed_by||"")}</small></div></div><details><summary>${__("View schedule snapshot")}</summary><div class="table-responsive"><table class="table table-bordered table-sm"><thead><tr><th>${__("Day")}</th><th>${__("Working Hours")}</th><th>${__("From Time")}</th><th>${__("To Time")}</th></tr></thead><tbody>${snapshot}</tbody></table></div></details></article>`;
		}).join("") || `<p class="text-muted">${__("No work schedule changes yet.")}</p>`;
		field.$wrapper.html(`<div class="schedule-workspace frappe-card"><div class="schedule-tabs"><button class="active" data-schedule-tab="current">${__("Current Work Schedule")}</button><button data-schedule-tab="history">${__("Past Schedules and Changes")} <span class="badge">${data.revision_count||0}</span></button></div><div class="schedule-panel" data-schedule-panel="current"><div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__("Day")}</th><th>${__("Working Hours")}</th><th>${__("From Time")}</th><th>${__("To Time")}</th></tr></thead><tbody>${currentRows}</tbody></table></div><button class="btn btn-primary btn-sm edit-work-schedule">${rows.length ? __("Edit Current Schedule") : __("Create Work Schedule")}</button></div><div class="schedule-panel hide" data-schedule-panel="history">${history}</div></div>`);
		field.$wrapper.find("[data-schedule-tab]").on("click", function(){const tab=$(this).data("schedule-tab");field.$wrapper.find("[data-schedule-tab]").removeClass("active");$(this).addClass("active");field.$wrapper.find("[data-schedule-panel]").addClass("hide");field.$wrapper.find(`[data-schedule-panel="${tab}"]`).removeClass("hide");});
		field.$wrapper.find(".edit-work-schedule").on("click", () => open_work_schedule_dialog(frm, data));
	} catch (error) {
		field.$wrapper.html(`<div class="text-danger p-3">${frappe.utils.escape_html(error.message||error)}</div>`);
	}
}

function open_work_schedule_dialog(frm, data) {
	const dialog = new frappe.ui.Dialog({
		title: data.rows?.length ? __("Edit Current Work Schedule") : __("Create Work Schedule"), size:"extra-large",
		fields:[
			{fieldname:"effective_from",label:__("Effective From"),fieldtype:"Date",reqd:1,default:frappe.datetime.get_today()},
			{fieldname:"action_date",label:__("Action Date"),fieldtype:"Date",reqd:1,default:frappe.datetime.get_today()},
			{fieldname:"change_summary",label:__("Reason for Change"),fieldtype:"Small Text"},
			{fieldname:"schedule",label:__("Weekly Work Schedule"),fieldtype:"Table",cannot_add_rows:false,in_place_edit:true,data:data.rows||[],fields:schedule_table_fields()},
		],
		primary_action_label:__("Save Work Schedule"),
		async primary_action(values){dialog.disable_primary_action();try{await frappe.call({method:"hr_custom.services.work_schedule_profile.save_profile",type:"POST",args:{payload:JSON.stringify({employee:frm.doc.name,effective_from:values.effective_from,action_date:values.action_date,change_summary:values.change_summary,rows:dialog.get_value("schedule")||[]})}});dialog.hide();await frm.reload_doc();}finally{dialog.enable_primary_action();}},
	});
	const grid = dialog.fields_dict.schedule.grid;
	grid.add_custom_button(__("Duplicate Selected Row"), () => duplicate_schedule_row(dialog));
	grid.add_custom_button(__("Complete Week to Saturday"), () => complete_schedule_week(dialog));
	dialog.show();
}

function selected_schedule_template(dialog) {
	const selected = dialog.fields_dict.schedule.grid.get_selected_children();
	if (selected.length !== 1) { frappe.msgprint(__("Select exactly one schedule row first.")); return null; }
	return selected[0];
}

function append_schedule_row(dialog, template, day) {
	const rows = dialog.get_value("schedule") || [];
	rows.push({day_of_week:day,working_hours:template.working_hours,from_time:template.from_time,to_time:template.to_time||end_time(template.from_time,template.working_hours),enabled:1});
	dialog.fields_dict.schedule.df.data = rows;
	dialog.fields_dict.schedule.grid.refresh();
}

function duplicate_schedule_row(dialog) {
	const template = selected_schedule_template(dialog); if (!template) return;
	const used = new Set((dialog.get_value("schedule")||[]).map(row=>row.day_of_week));
	const day = HR_CUSTOM_DAYS.find(value=>!used.has(value));
	if (!day) return frappe.msgprint(__("All days are already configured."));
	append_schedule_row(dialog, template, day);
}

function complete_schedule_week(dialog) {
	const template = selected_schedule_template(dialog); if (!template) return;
	const used = new Set((dialog.get_value("schedule")||[]).map(row=>row.day_of_week));
	HR_CUSTOM_DAYS.slice(0,6).filter(day=>!used.has(day)).forEach(day=>append_schedule_row(dialog,template,day));
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
