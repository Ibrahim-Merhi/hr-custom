frappe.ui.form.on("Attendance Correction Request", {
	refresh(frm) {
		const pending = ["Pending Approver Approval", "Pending HR Approval"].includes(frm.doc.approval_stage);
		if (!pending || frm.doc.docstatus === 2) return;
		const is_hr = frappe.user.has_role("HR Manager") || frappe.user.has_role("System Manager");
		const is_current_approver = frm.doc.approval_stage === "Pending Approver Approval" && frm.doc.current_approver === frappe.session.user;
		if (!is_hr && !is_current_approver) return;
		frm.add_custom_button(__("Approve"), () => correction_action(frm, "approve"), __("Actions"));
		frm.add_custom_button(__("Reject"), () => correction_action(frm, "reject"), __("Actions"));
		frm.page.set_primary_action(__("Approve"), () => correction_action(frm, "approve"));
	},
});

function correction_action(frm, action) {
	const is_override = (frappe.user.has_role("HR Manager") || frappe.user.has_role("System Manager"))
		&& frm.doc.approval_stage === "Pending Approver Approval"
		&& frm.doc.current_approver !== frappe.session.user;
	frappe.prompt([{
		fieldname: "remarks",
		label: is_override ? __("HR Override Note") : __("Approval Note"),
		fieldtype: "Small Text",
		reqd: is_override,
		description: is_override ? __("Required because HR is bypassing the configured employee approver(s).") : "",
	}], (values) => frappe.call({
		method: "hr_custom.api.attendance_correction_workflow.process_correction_approval",
		args: {name: frm.doc.name, action, remarks: values.remarks},
		freeze: true,
		freeze_message: action === "approve" ? __("Approving correction…") : __("Rejecting correction…"),
		callback: () => frm.reload_doc(),
	}), action === "approve" ? __("Approve Attendance Correction") : __("Reject Attendance Correction"), action === "approve" ? __("Approve") : __("Reject"));
}
