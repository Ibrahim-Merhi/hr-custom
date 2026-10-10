from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.password import update_password

from hr_custom.services.portal_identity import has_portal_role


EMPLOYEE_EDIT_FIELDS = {
	"employee_name", "first_name", "middle_name", "last_name", "gender",
	"date_of_birth", "date_of_joining", "status", "company", "department",
	"designation", "branch", "employment_type", "cell_number", "personal_email",
	"company_email", "holiday_list", "reports_to",
}
EMPLOYEE_DETAIL_FIELDS = ["name", *sorted(EMPLOYEE_EDIT_FIELDS), "image", "user_id"]


def _require_admin():
	if not has_portal_role("Portal Administrator"):
		frappe.throw(_("Portal Administrator access is required."), frappe.PermissionError)


def _page(start=0, page_length=50):
	return max(0, cint(start)), max(1, min(cint(page_length) or 50, 200))


@frappe.whitelist()
def get_overview():
	_require_admin()
	return {
		"employees": frappe.db.count("Employee"),
		"active_employees": frappe.db.count("Employee", {"status": "Active"}),
		"pending_leaves": frappe.db.count("Leave Application", {"docstatus": 0}),
		"attendance_today": frappe.db.count("Attendance", {"attendance_date": frappe.utils.nowdate(), "docstatus": 1}),
		"portal_accounts": frappe.db.count("Employee Portal Credential", {"employee": ["is", "set"]}),
	}


@frappe.whitelist()
def get_employees(search=None, start=0, page_length=50):
	_require_admin()
	start, page_length = _page(start, page_length)
	filters = []
	if (search or "").strip():
		term = f"%{search.strip()}%"
		filters = [["Employee", "name", "like", term], ["Employee", "employee_name", "like", term]]
		rows = frappe.db.sql(
			"""select name, employee_name, status, company, department, designation, branch, cell_number
			from `tabEmployee` where name like %(term)s or employee_name like %(term)s
			order by employee_name asc limit %(start)s, %(page_length)s""",
			{"term": term, "start": start, "page_length": page_length}, as_dict=True,
		)
	else:
		rows = frappe.get_all("Employee", fields=["name", "employee_name", "status", "company", "department", "designation", "branch", "cell_number"], order_by="employee_name asc", start=start, page_length=page_length)
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
	return {"changed": True}


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
def get_attendance(search=None, start=0, page_length=50):
	_require_admin()
	start, page_length = _page(start, page_length)
	filters = {}
	if (search or "").strip():
		filters["employee_name"] = ["like", f"%{search.strip()}%"]
	return frappe.get_all(
		"Attendance", filters=filters,
		fields=["name", "employee", "employee_name", "attendance_date", "status", "in_time", "out_time", "working_hours", "late_entry", "early_exit", "docstatus"],
		order_by="attendance_date desc, modified desc", start=start, page_length=page_length,
	)
