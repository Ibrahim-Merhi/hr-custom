from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate
from frappe.utils.password import update_password

from hr_custom.services.portal_identity import has_portal_role, run_portal_document_as_system_user


EMPLOYEE_EDIT_FIELDS = {
	"employee_name", "first_name", "middle_name", "last_name", "gender",
	"date_of_birth", "date_of_joining", "status", "company", "department",
	"designation", "branch", "employment_type", "cell_number", "personal_email",
	"company_email", "holiday_list", "reports_to",
}
EMPLOYEE_DETAIL_FIELDS = ["name", *sorted(EMPLOYEE_EDIT_FIELDS), "image", "user_id", "attendance_device_id"]
PORTAL_URL = "/attendance"


def _real_employee_filters(extra=None):
	filters = {"name": ["like", "HR-EMP-%"]}
	if frappe.get_meta("Employee").has_field("custom_is_payroll_identity"):
		filters["custom_is_payroll_identity"] = 0
	filters.update(extra or {})
	return filters


def _ensure_real_employee(employee):
	row = frappe.db.get_value("Employee", employee, ["name", "employee_name", "cell_number", "attendance_device_id", "user_id", "custom_is_payroll_identity"], as_dict=True)
	if not row or not row.name.startswith("HR-EMP-") or cint(row.get("custom_is_payroll_identity")):
		frappe.throw(_("Employee not found."))
	return row


def _share_payload(employee, username, password, desk=False):
	base_url = frappe.utils.get_url()
	url = f"{base_url}/login" if desk else f"{base_url}{PORTAL_URL}"
	label = _("ERPNext Desk") if desk else _("Employee HR Portal")
	message = _("Hello {0},\n\nYour {1} access is ready.\nUsername: {2}\nPassword: {3}\nLink: {4}\n\nPlease change your password after signing in and do not share it.").format(
		employee.employee_name, label, username, password, url
	)
	return {"message": message, "phone": employee.cell_number or "", "url": url, "username": username}


def _require_admin():
	if not has_portal_role("Portal Administrator"):
		frappe.throw(_("Portal Administrator access is required."), frappe.PermissionError)


def _page(start=0, page_length=50):
	return max(0, cint(start)), max(1, min(cint(page_length) or 50, 200))


@frappe.whitelist()
def get_overview():
	_require_admin()
	return {
		"employees": frappe.db.count("Employee", _real_employee_filters()),
		"active_employees": frappe.db.count("Employee", _real_employee_filters({"status": "Active"})),
		"pending_leaves": frappe.db.count("Leave Application", {"docstatus": 0}),
		"attendance_today": frappe.db.count("Attendance", {"attendance_date": frappe.utils.nowdate(), "docstatus": 1}),
		"portal_accounts": frappe.db.count("Employee Portal Credential", {"employee": ["is", "set"]}),
	}


@frappe.whitelist()
def get_employees(search=None, start=0, page_length=50):
	_require_admin()
	start, page_length = _page(start, page_length)
	real_clause = " and name like 'HR-EMP-%%'"
	if frappe.get_meta("Employee").has_field("custom_is_payroll_identity"):
		real_clause += " and coalesce(custom_is_payroll_identity, 0) = 0"
	if (search or "").strip():
		term = f"%{search.strip()}%"
		rows = frappe.db.sql(
			f"""select name, employee_name, status, company, department, designation, branch, cell_number
			from `tabEmployee` where (name like %(term)s or employee_name like %(term)s) {real_clause}
			order by employee_name asc limit %(start)s, %(page_length)s""",
			{"term": term, "start": start, "page_length": page_length}, as_dict=True,
		)
	else:
		rows = frappe.get_all("Employee", filters=_real_employee_filters(), fields=["name", "employee_name", "status", "company", "department", "designation", "branch", "cell_number"], order_by="employee_name asc", start=start, page_length=page_length)
	credentials = {
		row.employee: row for row in frappe.get_all(
			"Employee Portal Credential", filters={"employee": ["in", [row.name for row in rows]]},
			fields=["name", "employee", "username", "enabled", "last_login"],
		)
	} if rows else {}
	for row in rows:
		credential = credentials.get(row.name)
		row.update({
			"portal_credential": credential.name if credential else None,
			"portal_username": credential.username if credential else None,
			"portal_enabled": cint(credential.enabled) if credential else 0,
			"last_login": credential.last_login if credential else None,
		})
	return rows


@frappe.whitelist()
def get_employee(employee):
	_require_admin()
	_ensure_real_employee(employee)
	available = [field for field in EMPLOYEE_DETAIL_FIELDS if field == "name" or frappe.get_meta("Employee").has_field(field)]
	row = frappe.db.get_value("Employee", employee, available, as_dict=True)
	if not row:
		frappe.throw(_("Employee not found."))
	row.portal = frappe.db.get_value(
		"Employee Portal Credential", {"employee": employee},
		["name", "username", "enabled", "last_login", "language"], as_dict=True,
	)
	return row


@frappe.whitelist(methods=["POST"])
def create_employee(values):
	_require_admin()
	if isinstance(values, str):
		values = frappe.parse_json(values)
	values = values if isinstance(values, dict) else {}
	required = ("first_name", "gender", "date_of_birth", "date_of_joining", "company", "branch")
	missing = [field for field in required if not values.get(field)]
	if missing:
		frappe.throw(_("Please complete: {0}").format(", ".join(missing)))
	doc = frappe.new_doc("Employee")
	for field in EMPLOYEE_EDIT_FIELDS:
		if field in values and doc.meta.has_field(field):
			doc.set(field, values[field] or None)
	doc.status = values.get("status") or "Active"
	if doc.meta.has_field("custom_branches"):
		doc.append("custom_branches", {"company": doc.company, "branch": doc.branch, "department": doc.department, "designation": doc.designation, "employment_type": doc.employment_type, "from_date": doc.date_of_joining})
	doc.insert(ignore_permissions=True)
	doc.add_comment("Info", _("Created from Portal Administrator by {0}.").format(frappe.session.user))
	return {"created": True, "employee": doc.name}


@frappe.whitelist(methods=["POST"])
def update_employee(employee, values):
	_require_admin()
	if isinstance(values, str):
		values = frappe.parse_json(values)
	if not isinstance(values, dict):
		frappe.throw(_("Invalid employee values."))
	doc = frappe.get_doc("Employee", employee)
	changed = []
	for fieldname, value in values.items():
		if fieldname not in EMPLOYEE_EDIT_FIELDS or not doc.meta.has_field(fieldname):
			continue
		doc.set(fieldname, value or None)
		changed.append(fieldname)
	if not changed:
		frappe.throw(_("No supported employee fields were supplied."))
	doc.flags.ignore_permissions = True
	doc.save()
	doc.add_comment("Info", _("Updated from Portal Administrator by {0}. Fields: {1}").format(frappe.session.user, ", ".join(changed)))
	return {"saved": True, "employee": doc.name}


@frappe.whitelist(methods=["POST"])
def set_employee_portal_password(employee, password):
	_require_admin()
	employee_row = _ensure_real_employee(employee)
	password = password or ""
	if len(password) < 12:
		frappe.throw(_("The new portal password must contain at least 12 characters."))
	credential = frappe.db.get_value("Employee Portal Credential", {"employee": employee}, "name")
	if not credential:
		frappe.throw(_("This employee does not have a portal credential."))
	update_password(credential, password, doctype="Employee Portal Credential", fieldname="password")
	frappe.db.set_value("Employee Portal Session", {"credential": credential}, "revoked", 1, update_modified=False)
	frappe.get_doc("Employee Portal Credential", credential).add_comment(
		"Info", _("Portal password reset and active sessions revoked by {0}.").format(frappe.session.user)
	)
	return {"changed": True, "share": _share_payload(employee_row, frappe.db.get_value("Employee Portal Credential", credential, "username"), password)}


@frappe.whitelist(methods=["POST"])
def create_employee_portal_access(employee, username, password):
	_require_admin()
	employee_row = _ensure_real_employee(employee)
	if frappe.db.exists("Employee Portal Credential", {"employee": employee}):
		frappe.throw(_("This employee already has portal access."))
	username = (username or employee_row.attendance_device_id or "").strip()
	if not username:
		frappe.throw(_("Enter a portal username or set the Employee Attendance Device ID."))
	if len(password or "") < 12:
		frappe.throw(_("The portal password must contain at least 12 characters."))
	doc = frappe.get_doc({"doctype": "Employee Portal Credential", "account_type": "Employee", "employee": employee, "username": username, "password": password, "enabled": 1})
	doc.append("roles", {"portal_role": "Employee"})
	actor = frappe.session.user
	with run_portal_document_as_system_user():
		doc.insert(ignore_permissions=True)
		doc.add_comment("Info", _("Portal access created by {0}.").format(actor))
	return {"created": True, "credential": doc.name, "share": _share_payload(employee_row, username, password)}


@frappe.whitelist(methods=["POST"])
def set_employee_desk_password(employee, password):
	_require_admin()
	employee_row = _ensure_real_employee(employee)
	if not employee_row.user_id or not frappe.db.exists("User", employee_row.user_id):
		frappe.throw(_("This employee is not linked to a Desk User."))
	if len(password or "") < 12:
		frappe.throw(_("The Desk password must contain at least 12 characters."))
	update_password(employee_row.user_id, password)
	frappe.db.delete("Sessions", {"user": employee_row.user_id})
	frappe.get_doc("Employee", employee).add_comment("Info", _("Desk password reset and sessions revoked by {0}.").format(frappe.session.user))
	return {"changed": True, "share": _share_payload(employee_row, employee_row.user_id, password, desk=True)}


@frappe.whitelist(methods=["POST"])
def set_employee_portal_enabled(employee, enabled):
	_require_admin()
	credential = frappe.db.get_value("Employee Portal Credential", {"employee": employee}, "name")
	if not credential:
		frappe.throw(_("This employee does not have a portal credential."))
	enabled = cint(enabled)
	frappe.db.set_value("Employee Portal Credential", credential, "enabled", enabled)
	if not enabled:
		frappe.db.set_value("Employee Portal Session", {"credential": credential}, "revoked", 1, update_modified=False)
	return {"enabled": enabled}


@frappe.whitelist()
def get_leaves(search=None, start=0, page_length=50):
	_require_admin()
	start, page_length = _page(start, page_length)
	filters = {}
	if (search or "").strip():
		filters["employee_name"] = ["like", f"%{search.strip()}%"]
	return frappe.get_all(
		"Leave Application", filters=filters,
		fields=["name", "employee", "employee_name", "leave_type", "from_date", "to_date", "total_leave_days", "status", "custom_approval_stage", "docstatus", "creation"],
		order_by="creation desc", start=start, page_length=page_length,
	)


@frappe.whitelist()
def get_form_options(employee=None):
	_require_admin()
	result = {
		"employees": frappe.get_all("Employee", filters=_real_employee_filters({"status": "Active"}), fields=["name", "employee_name", "company", "cell_number"], order_by="employee_name asc", limit_page_length=500),
		"companies": frappe.get_all("Company", pluck="name", order_by="name asc", limit_page_length=500),
		"leave_types": frappe.get_all("Leave Type", filters={"is_lwp": 0}, fields=["name", "custom_leave_unit"], order_by="name asc", limit_page_length=200),
	}
	if employee:
		_ensure_real_employee(employee)
		result["allocations"] = frappe.get_all("Leave Allocation", filters={"employee": employee, "docstatus": 1, "to_date": [">=", nowdate()]}, fields=["leave_type"], distinct=True, order_by="leave_type asc")
	return result


@frappe.whitelist(methods=["POST"])
def create_leave_application(employee, leave_type, from_date, to_date, reason, half_day=0):
	_require_admin()
	_ensure_real_employee(employee)
	from hr_custom.services.portal_identity import run_portal_document_as_system_user
	from hr_custom.services.simple_leave import calculate_leave_calendar, get_leave_application_employee_defaults
	start, end = getdate(from_date), getdate(to_date)
	if end < start:
		frappe.throw(_("To Date cannot be before From Date."))
	if not (reason or "").strip():
		frappe.throw(_("Please enter the reason for the leave."))
	preview = calculate_leave_calendar(employee, leave_type, start, end, None, None, cint(half_day))
	defaults = get_leave_application_employee_defaults(employee)
	doc = frappe.get_doc({"doctype": "Leave Application", "employee": employee, "company": defaults["company"], "leave_type": leave_type, "from_date": start, "to_date": end, "half_day": cint(half_day), "half_day_date": start if cint(half_day) else None, "posting_date": nowdate(), "description": reason.strip(), "leave_approver": defaults["leave_approver"], "status": "Open"})
	with run_portal_document_as_system_user():
		doc.flags.skip_standard_leave_notification = True
		doc.insert(ignore_permissions=True, ignore_links=True)
	doc.add_comment("Info", _("Created for the employee from Portal Administrator by {0}.").format(frappe.session.user))
	return {"created": True, "name": doc.name, "leave_days": preview.get("leave_days")}


@frappe.whitelist(methods=["POST"])
def create_yearly_leave_allocation(employee, leave_type, allocated_amount, allocation_year, from_date, to_date):
	_require_admin()
	employee_row = _ensure_real_employee(employee)
	amount = frappe.utils.flt(allocated_amount)
	if amount <= 0:
		frappe.throw(_("Allocated amount must be greater than zero."))
	employee_doc = frappe.get_doc("Employee", employee)
	unit = frappe.db.get_value("Leave Type", leave_type, "custom_leave_unit") or "Days"
	doc = frappe.get_doc({"doctype": "Yearly Leave Allocation", "company": employee_doc.company, "allocation_year": cint(allocation_year), "from_date": getdate(from_date), "to_date": getdate(to_date), "description": _("Created from Portal Administrator")})
	doc.append("employees", {"employee": employee, "employee_name": employee_row.employee_name, "attendance_device_id": employee_doc.attendance_device_id, "department": employee_doc.department, "branch": employee_doc.branch, "designation": employee_doc.designation, "employment_type": employee_doc.employment_type, "employee_status": employee_doc.status, "is_active": 1})
	doc.append("allocations", {"employee": employee, "employee_name": employee_row.employee_name, "leave_type": leave_type, "leave_unit": unit, "allocated_amount": amount, "from_date": doc.from_date, "to_date": doc.to_date, "allocation_status": "Pending"})
	doc.insert(ignore_permissions=True)
	doc.add_comment("Info", _("Draft allocation created from Portal Administrator by {0}.").format(frappe.session.user))
	return {"created": True, "name": doc.name, "status": doc.status}


@frappe.whitelist()
def get_attendance(search=None, from_date=None, to_date=None, start=0, page_length=50, export=0):
	_require_admin()
	start, page_length = _page(start, page_length)
	end = getdate(to_date or nowdate())
	begin = getdate(from_date or add_days(end, -30))
	if end < begin:
		frappe.throw(_("To Date cannot be before From Date."))
	if (end - begin).days > 366:
		frappe.throw(_("Choose a date range of 366 days or less."))
	filters = {"attendance_date": ["between", [begin, end]]}
	if (search or "").strip():
		filters["employee_name"] = ["like", f"%{search.strip()}%"]
	if frappe.get_meta("Employee").has_field("custom_is_payroll_identity"):
		real_employees = frappe.get_all("Employee", filters=_real_employee_filters(), pluck="name")
		filters["employee"] = ["in", real_employees or [""]]
	return frappe.get_all(
		"Attendance", filters=filters,
		fields=["name", "employee", "employee_name", "attendance_date", "status", "in_time", "out_time", "working_hours", "late_entry", "early_exit", "docstatus"],
		order_by="attendance_date desc, employee_name asc", start=0 if cint(export) else start, page_length=0 if cint(export) else page_length,
	)
