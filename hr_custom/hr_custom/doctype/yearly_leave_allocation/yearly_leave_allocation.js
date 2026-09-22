frappe.ui.form.on("Yearly Leave Allocation", {
  setup(frm) {
    frappe.dom.set_style(`
      .yla-inline-grid .btn-open-row { display: none !important; }
      .yla-inline-grid .grid-static-col[data-fieldname="allocated_amount"] { cursor: text; }
    `);
    frm.set_query("company", () => ({ filters: { is_group: 0 } }));
    if (!frm.doc.company) frm.set_value("company", frappe.defaults.get_user_default("Company"));
  },
  allocation_year(frm) {
    if (!frm.doc.allocation_year || frm.doc.from_date || frm.doc.to_date) return;
    frm.set_value("from_date", `${frm.doc.allocation_year}-01-01`);
    frm.set_value("to_date", `${frm.doc.allocation_year}-12-31`);
  },
  refresh(frm) {
    frm.fields_dict.allocations?.grid?.wrapper?.addClass("yla-inline-grid");
    if (frm.doc.docstatus === 0 && !frm.is_new()) {
      frm.add_custom_button(__("Generate Employees"), () => call_action(frm, "generate_employees"), __("Prepare"));
      frm.add_custom_button(__("Generate Allowances"), () => call_action(frm, "generate_allowances"), __("Prepare"));
      frm.add_custom_button(__("Link Existing Allocations"), () => link_existing(frm), __("Prepare"));
      frm.add_custom_button(__("Consolidate Duplicate Rows"), () => consolidate_duplicates(frm), __("Prepare"));
      frm.add_custom_button(__("Copy Previous Year"), () => call_action(frm, "copy_previous_year"), __("Prepare"));
      frm.add_custom_button(__("Validate & Preview"), () => preview(frm));
    }
    if (frm.doc.docstatus === 1 && ["Failed", "Partially Completed"].includes(frm.doc.status)) {
      frm.add_custom_button(__("Retry Failed Allocations"), () => call_action(frm, "hr_custom.services.yearly_leave_allocation.retry_generation"));
      frm.add_custom_button(__("View Failed Reasons"), () => show_failed_reasons(frm));
    }
    if (frm.doc.docstatus === 1) {
      frm.add_custom_button(__("New Employee Allocation"), () => new_employee_allocation(frm), __("Adjustments"));
      frm.dashboard.set_headline_alert(__("Allocated amounts may be adjusted here by HR Manager. Changes update the submitted Leave Allocation and its ledger. Use New Employee Allocation for mid-year hires."), "blue");
    }
    if (frm.doc.status === "Processing") {
      frm.dashboard.set_headline_alert(__("Standard Leave Allocations are being generated in the background."), "blue");
      setTimeout(() => frm.reload_doc(), 5000);
    }
  }
});

async function call_action(frm, method) {
  if (frm.is_dirty()) await frm.save();
  const full_method = method.includes(".") ? method : `hr_custom.hr_custom.doctype.yearly_leave_allocation.yearly_leave_allocation.${method}`;
  const response = await frappe.call({ method: full_method, args: { name: frm.doc.name }, freeze: true, freeze_message: __("Processing…") });
  // The server changes child tables outside the form's local document model.
  // Reload from the database, then explicitly repaint both grids.
  await frm.reload_doc();
  frm.refresh_fields(["employees", "allocations", "total_employees", "total_allocations", "status"]);
  frm.fields_dict.employees?.grid?.refresh();
  frm.fields_dict.allocations?.grid?.refresh();
  frappe.show_alert({ message: __("Updated successfully"), indicator: "green" });
  return response.message;
}

function show_failed_reasons(frm) {
  const failed = (frm.doc.allocations || []).filter(row => row.allocation_status === "Failed");
  if (!failed.length) {
    frappe.msgprint({ message: __("No failed allocation rows were found."), indicator: "green" });
    return;
  }
  const rows = failed.map(row => {
    const reason = frappe.utils.escape_html(String(row.error_message || __("No failure reason was recorded.")).replace(/<[^>]*>/g, ""));
    return `<tr><td>${row.idx}</td><td>${frappe.utils.escape_html(row.employee_name || row.employee || "")}</td><td>${frappe.utils.escape_html(row.leave_type || "")}</td><td>${reason}</td></tr>`;
  }).join("");
  frappe.msgprint({
    title: __("Failed Allocation Reasons"),
    wide: true,
    indicator: "red",
    message: `<p>${__("Correct the allocated amount directly in the table, or correct the employee/leave configuration, then use Retry Failed Allocations.")}</p><div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__("Row")}</th><th>${__("Employee")}</th><th>${__("Leave Type")}</th><th>${__("Reason")}</th></tr></thead><tbody>${rows}</tbody></table></div>`
  });
}

function new_employee_allocation(frm) {
  const dialog = new frappe.ui.Dialog({
    title: __("New Employee Allocation"),
    fields: [
      { fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee", reqd: 1,
        get_query: () => ({ filters: { company: frm.doc.company, status: "Active" } }) },
      { fieldname: "from_date", label: __("Allocation Start Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() }
    ],
    primary_action_label: __("Create Draft"),
    async primary_action(values) {
      const { message } = await frappe.call({
        method: "hr_custom.hr_custom.doctype.yearly_leave_allocation.yearly_leave_allocation.create_supplemental_allocation",
        args: { name: frm.doc.name, employee: values.employee, from_date: values.from_date },
        freeze: true,
        freeze_message: __("Creating supplemental allocation…")
      });
      dialog.hide();
      frappe.set_route("Form", "Yearly Leave Allocation", message.name);
    }
  });
  dialog.show();
}

async function preview(frm) {
  await frm.save();
  const { message } = await frappe.call({ method: "hr_custom.hr_custom.doctype.yearly_leave_allocation.yearly_leave_allocation.preview", args: { name: frm.doc.name } });
  const errors = (message.errors || []).map(value => `<li>${frappe.utils.escape_html(value)}</li>`).join("");
  frappe.msgprint({ title: __("Allocation Preview"), wide: true, indicator: errors ? "orange" : "green", message: `<div class="row"><div class="col-sm-4"><b>${__("Employees")}</b><br>${message.employees}</div><div class="col-sm-4"><b>${__("Day allocations")}</b><br>${message.day_rows}</div><div class="col-sm-4"><b>${__("Hour allocations")}</b><br>${message.hour_rows}</div></div>${errors ? `<hr><b>${__("Issues to resolve")}</b><ul>${errors}</ul>` : `<hr>${__("Ready to generate: {0}", [message.ready])}`}` });
}

async function link_existing(frm) {
  if (frm.is_dirty()) await frm.save();
  const { message } = await frappe.call({
    method: "hr_custom.services.yearly_leave_allocation.link_existing_allocations",
    args: { name: frm.doc.name },
    freeze: true,
    freeze_message: __("Matching existing Leave Allocations…")
  });
  await frm.reload_doc();
  frm.refresh_field("allocations");
  const details = (message.unresolved || []).map(value => `<li>${frappe.utils.escape_html(value)}</li>`).join("");
  frappe.msgprint({
    title: __("Existing Allocations Linked"),
    indicator: message.ambiguous ? "orange" : "green",
    message: `<p>${__("Linked {0} exact allocation(s). {1} row(s) were already linked.", [message.linked, message.already_linked])}</p>${details ? `<p>${__("These rows need HR review because more than one exact record exists:")}</p><ul>${details}</ul>` : ""}`
  });
}

async function consolidate_duplicates(frm) {
  if (frm.is_dirty()) await frm.save();
  const { message } = await frappe.call({
    method: "hr_custom.services.yearly_leave_allocation.consolidate_duplicate_rows",
    args: { name: frm.doc.name },
    freeze: true,
    freeze_message: __("Consolidating duplicate allocation rows…")
  });
  await frm.reload_doc();
  frm.refresh_field("allocations");
  frappe.msgprint({
    title: __("Duplicate Rows Consolidated"),
    indicator: "green",
    message: __("Merged {0} duplicate group(s), removed {1} repeated row(s), and removed {2} replaced draft allocation(s).", [message.merged, message.removed_rows, message.removed_allocations])
  });
}
