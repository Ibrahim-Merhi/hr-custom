frappe.ui.form.on("Attendance Exception", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Open") return;
		frm.add_custom_button(__("Create Correction Request"), () => {
			const supported = ["Missing Check In", "Missing Check Out"].includes(frm.doc.exception_type) ? frm.doc.exception_type : "Other";
			frappe.new_doc("Attendance Correction Request", {
				employee: frm.doc.employee,
				attendance_date: frm.doc.attendance_date,
				request_type: supported,
				reason: frm.doc.details || `${frm.doc.exception_type}: ${frm.doc.name}`,
			});
		}, __("Resolve"));
		frm.add_custom_button(__("Mark Resolved"), () => frappe.prompt([
			{fieldname: "resolution_notes", label: __("Resolution Notes"), fieldtype: "Small Text", reqd: 1},
		], (values) => frappe.call({
			method: "frappe.client.set_value",
			args: {doctype: frm.doctype, name: frm.doc.name, fieldname: {status: "Resolved", resolved_by: frappe.session.user, resolved_on: frappe.datetime.now_datetime(), resolution_notes: values.resolution_notes}},
			callback: () => frm.reload_doc(),
		}), __("Resolve Attendance Exception"), __("Mark Resolved")), __("Resolve"));
	},
});
