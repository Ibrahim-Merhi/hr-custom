from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document


PORTAL_ROLES = {"Employee", "Leave Approver", "HR", "Portal Administrator"}


class EmployeePortalCredential(Document):
	def autoname(self):
		if self.account_type == "Portal Administrator":
			self.name = f"PORTAL-ADMIN-{self.username}"
		elif self.employee:
			self.name = self.employee

	def validate(self):
		self.account_type = self.account_type or "Employee"
		if self.account_type == "Portal Administrator":
			if frappe.session.user != "Administrator":
				frappe.throw(_("Only Administrator can create or modify a Portal Administrator credential."), frappe.PermissionError)
			self.employee = None
			self.employee_name = None
		if self.employee and not self.username:
			self.username = frappe.db.get_value("Employee", self.employee, "attendance_device_id")
		self.username = (self.username or "").strip()
		if not self.username:
			frappe.throw(_("Enter a portal username. Employee credentials may use the Attendance Device ID."))
		if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", self.username):
			frappe.throw(_("Portal Username must be 3-80 characters and may contain letters, numbers, dots, underscores and hyphens."))
		if self.password and not self.is_dummy_password(self.password):
			self.flags.portal_plain_password = self.password

		roles = []
		for row in self.roles or []:
			if row.portal_role not in PORTAL_ROLES:
				frappe.throw(_("Unsupported portal role: {0}").format(row.portal_role))
			if row.portal_role not in roles:
				roles.append(row.portal_role)
		self.set("roles", [])
		if self.account_type == "Portal Administrator":
			roles = ["Portal Administrator"]
		for role in roles or ["Employee"]:
			self.append("roles", {"portal_role": role})
		if "Portal Administrator" in roles and frappe.session.user != "Administrator":
			frappe.throw(_("Only Administrator can grant Portal Administrator access."), frappe.PermissionError)

		if self.account_type != "Portal Administrator" and not self.employee:
			frappe.throw(_("Select an Employee for an employee portal credential."))
		if self.enabled and self.employee and frappe.db.get_value("Employee", self.employee, "status") != "Active":
			frappe.throw(_("Portal access can only be enabled for an active Employee."))

	def before_insert(self):
		pass

	def on_update(self):
		self._save_hashed_portal_password()
		if not self.enabled:
			frappe.db.set_value("Employee Portal Session", {"credential": self.name}, "revoked", 1, update_modified=False)

	def on_trash(self):
		if any(row.portal_role == "Portal Administrator" for row in self.roles or []) and frappe.session.user != "Administrator":
			frappe.throw(_("Only Administrator can delete a Portal Administrator credential."), frappe.PermissionError)
		frappe.db.delete("Employee Portal Session", {"credential": self.name})

	def _save_hashed_portal_password(self):
		plain_password = self.flags.get("portal_plain_password")
		if plain_password:
			from frappe.utils.password import update_password
			update_password(self.name, plain_password, doctype=self.doctype, fieldname="password")
			frappe.db.set_value("Employee Portal Session", {"credential": self.name}, "revoked", 1, update_modified=False)
