from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document


PORTAL_ROLES = {"Employee", "Leave Approver", "HR"}


class EmployeePortalCredential(Document):
	def validate(self):
		self.username = (self.username or "").strip().lower()
		if not self.username:
			frappe.throw(_("Portal Username is required."))
		if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", self.username):
			frappe.throw(_("Portal Username must be 3-80 characters and may contain letters, numbers, dots, underscores and hyphens."))

		roles = []
		for row in self.roles or []:
			if row.portal_role not in PORTAL_ROLES:
				frappe.throw(_("Unsupported portal role: {0}").format(row.portal_role))
			if row.portal_role not in roles:
				roles.append(row.portal_role)
		self.set("roles", [])
		for role in roles or ["Employee"]:
			self.append("roles", {"portal_role": role})

		if self.enabled and frappe.db.get_value("Employee", self.employee, "status") != "Active":
			frappe.throw(_("Portal access can only be enabled for an active Employee."))

	def before_insert(self):
		self.portal_user = self._ensure_website_user()

	def on_update(self):
		portal_user = self._ensure_website_user()
		if self.portal_user != portal_user:
			self.db_set("portal_user", portal_user, update_modified=False)

	def on_trash(self):
		if self.portal_user and frappe.db.exists("User", self.portal_user):
			frappe.db.set_value("User", self.portal_user, "enabled", 0, update_modified=False)

	def _ensure_website_user(self):
		user = self.portal_user or _portal_user_email(self.employee)
		employee_name = self.employee_name or frappe.db.get_value("Employee", self.employee, "employee_name") or self.employee
		if frappe.db.exists("User", user):
			values = frappe.db.get_value("User", user, ["user_type", "enabled"], as_dict=True)
			if values.user_type != "Website User":
				frappe.throw(_("The managed portal user {0} is not a Website User.").format(frappe.bold(user)))
			frappe.db.set_value("User", user, {"enabled": int(bool(self.enabled)), "first_name": employee_name}, update_modified=False)
			return user

		doc = frappe.get_doc({
			"doctype": "User",
			"email": user,
			"first_name": employee_name,
			"enabled": int(bool(self.enabled)),
			"user_type": "Website User",
			"send_welcome_email": 0,
		})
		doc.flags.no_welcome_mail = True
		doc.insert(ignore_permissions=True)
		return doc.name


def _portal_user_email(employee: str) -> str:
	safe_employee = re.sub(r"[^a-z0-9]+", ".", employee.lower()).strip(".")
	return f"portal.{safe_employee}@employees.invalid"
