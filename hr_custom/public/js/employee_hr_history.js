async function load_employee_hr_history(frm) {
  if (frm.is_new()) return;
  const leaveWrapper = frm.fields_dict.custom_leave_balances_html?.$wrapper;
  const attendanceWrapper = frm.fields_dict.custom_attendance_log_html?.$wrapper;
  if (!leaveWrapper || !attendanceWrapper) return;
  leaveWrapper.html(`<div class="text-muted">${__("Loading leave balances…")}</div>`);
  attendanceWrapper.html(`<div class="text-muted">${__("Loading attendance log…")}</div>`);
  try {
    const { message } = await frappe.call({
      method: "hr_custom.services.employee_profile.get_employee_hr_history",
      args: { employee: frm.doc.name }
    });
    leaveWrapper.html(render_leave_balances(message.balances || [], frm.doc.name));
    bind_used_leave_links(leaveWrapper);
    attendanceWrapper.html(render_attendance_log(message.attendance || []));
  } catch (error) {
    const failed = `<div class="text-danger">${__("Unable to load HR history. Please refresh and try again.")}</div>`;
    leaveWrapper.html(failed);
    attendanceWrapper.html(failed);
  }
}

window.hr_custom_load_employee_hr_history = load_employee_hr_history;

function history_table(headers, rows, emptyMessage) {
  if (!rows.length) return `<div class="text-muted p-3">${emptyMessage}</div>`;
  return `<div class="table-responsive"><table class="table table-bordered table-hover">
    <thead><tr>${headers.map(value => `<th>${value}</th>`).join("")}</tr></thead>
    <tbody>${rows.join("")}</tbody></table></div>`;
}

function cell(value) {
  return frappe.utils.escape_html(value === null || value === undefined || value === "" ? "—" : String(value));
}

function render_leave_balances(rows, employee) {
  return history_table(
    [__("Leave Type"), __("Unit"), __("Allocated"), __("Used"), __("Remaining"), __("Period")],
    rows.map(row => {
      const used = flt(row.used);
      const usedValue = used > 0
        ? `<a href="#" class="used-leaves-link" data-employee="${cell(employee)}" data-leave-type="${cell(row.leave_type)}" data-from-date="${cell(row.from_date)}" data-to-date="${cell(row.to_date)}" title="${__("Open used leave applications")}">${cell(row.used)}</a>`
        : cell(row.used);
      return `<tr><td>${cell(row.leave_type)}</td><td>${cell(__(row.unit))}</td><td>${cell(row.allocated)}</td><td>${usedValue}</td><td><b>${cell(row.remaining)}</b></td><td>${cell(frappe.datetime.str_to_user(row.from_date))} – ${cell(frappe.datetime.str_to_user(row.to_date))}</td></tr>`;
    }),
    __("No active leave allocations were found for this employee.")
  );
}

function bind_used_leave_links(wrapper) {
  wrapper.off("click.hr_custom_used_leave", ".used-leaves-link");
  wrapper.on("click.hr_custom_used_leave", ".used-leaves-link", function (event) {
    event.preventDefault();
    const link = this.dataset;
    frappe.route_options = {
      employee: link.employee,
      leave_type: link.leaveType,
      status: "Approved",
      docstatus: 1,
      from_date: ["<=", link.toDate],
      to_date: [">=", link.fromDate],
    };
    frappe.set_route("List", "Leave Application");
  });
}

function render_attendance_log(rows) {
  return history_table(
    [__("Date"), __("Status"), __("Check In"), __("Check Out"), __("Hours"), __("Check-in Branch"), __("Check-out Branch")],
    rows.map(row => `<tr><td><a href="/app/attendance/${encodeURIComponent(row.name)}">${cell(frappe.datetime.str_to_user(row.attendance_date))}</a></td><td>${cell(__(row.status))}</td><td>${cell(row.in_time ? frappe.datetime.str_to_user(row.in_time) : null)}</td><td>${cell(row.out_time ? frappe.datetime.str_to_user(row.out_time) : null)}</td><td>${cell(flt_value(row.working_hours))}</td><td>${cell(row.custom_check_in_branch)}</td><td>${cell(row.custom_check_out_branch)}</td></tr>`),
    __("No attendance records were found for this employee.")
  );
}

function flt_value(value) {
  return Number(value || 0).toFixed(2);
}
