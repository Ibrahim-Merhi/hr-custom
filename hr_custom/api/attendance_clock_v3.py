"""Portal attendance commands with UI-safe validation responses.

Expected attendance validation failures are returned as ordinary data so the
PWA can present them with its own dialog instead of Frappe's generic msgprint.
"""

import importlib

import frappe


def _api():
	from hr_custom.api import mobile_attendance

	return importlib.reload(mobile_attendance)


@frappe.whitelist(methods=["POST"])
def submit_checkin(
	latitude=None,
	longitude=None,
	accuracy=None,
	device_info=None,
	device_id=None,
	request_id=None,
):
	try:
		result = _api().submit_checkin(
			latitude,
			longitude,
			accuracy,
			device_info,
			device_id,
			request_id,
		)
		return {"ok": True, "result": result}
	except frappe.ValidationError as error:
		# Do not leak the validation into Frappe's global message queue. The
		# employee portal renders this message in its branded location dialog.
		frappe.clear_messages()
		return {"ok": False, "message": str(error)}
