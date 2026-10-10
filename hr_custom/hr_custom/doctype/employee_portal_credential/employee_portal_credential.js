frappe.ui.form.on("Employee Portal Credential", {
	account_type(frm) {
		if (frm.doc.account_type !== "Portal Administrator") return;
		frm.set_value("employee", null);
		frm.clear_table("roles");
		frm.add_child("roles", {portal_role: "Portal Administrator"});
		frm.refresh_field("roles");
	},
	refresh(frm) {
		if (frappe.session.user !== "Administrator" || frm.is_new() || !frm.doc.enabled || frm.doc.account_type === "Portal Administrator") return;

		frm.add_custom_button(__("Impersonate Portal"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Impersonate Employee Portal"),
				fields: [{
					fieldname: "reason",
					label: __("Troubleshooting Reason"),
					fieldtype: "Small Text",
					reqd: 1,
					description: __("This action is audited and expires automatically after 30 minutes."),
				}],
				primary_action_label: __("Start Impersonation"),
				async primary_action(values) {
					const portalWindow = window.open("about:blank", "_blank");
					dialog.get_primary_btn().prop("disabled", true);
					try {
						await frappe.call({
							method: "hr_custom.api.portal_auth.start_impersonation",
							type: "POST",
							args: {credential: frm.doc.name, reason: values.reason},
						});
						dialog.hide();
						if (portalWindow) portalWindow.location.replace(`/attendance?impersonation=${Date.now()}`);
						else window.location.assign(`/attendance?impersonation=${Date.now()}`);
					} catch (error) {
						portalWindow?.close();
						throw error;
					} finally {
						dialog.get_primary_btn().prop("disabled", false);
					}
				},
			});
			dialog.show();
		}, __("Actions"));
	},
});
