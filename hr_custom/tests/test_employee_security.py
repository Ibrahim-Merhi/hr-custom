from unittest import TestCase
from unittest.mock import patch

import frappe

from hr_custom.services.employee_security import validate_location_bypass_permission


class TestEmployeeSecurity(TestCase):
	def _employee_change(self, before, after):
		doc = frappe._dict(custom_location_not_required=after)
		doc.get_doc_before_save = lambda: frappe._dict(custom_location_not_required=before)
		return doc

	@patch("hr_custom.services.employee_security.can_manage_location_bypass", return_value=False)
	def test_unauthorized_user_cannot_change_location_bypass(self, _can_manage):
		with patch("hr_custom.services.employee_security._", side_effect=lambda message: message), patch(
			"hr_custom.services.employee_security.frappe.throw", side_effect=frappe.PermissionError
		):
			with self.assertRaises(frappe.PermissionError):
				validate_location_bypass_permission(self._employee_change(0, 1))

	@patch("hr_custom.services.employee_security.can_manage_location_bypass", return_value=True)
	def test_authorized_user_can_change_location_bypass(self, _can_manage):
		validate_location_bypass_permission(self._employee_change(0, 1))

	@patch("hr_custom.services.employee_security.can_manage_location_bypass", return_value=False)
	def test_unchanged_value_remains_valid_for_other_roles(self, _can_manage):
		validate_location_bypass_permission(self._employee_change(1, 1))
