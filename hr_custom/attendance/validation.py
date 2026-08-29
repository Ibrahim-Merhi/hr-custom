import frappe
from frappe import _
from frappe.utils import flt


def validate_branch(doc, method=None):
    if not doc.get("custom_enable_mobile_attendance"):
        return
    lat, lon = doc.get("custom_branch_latitude"), doc.get("custom_branch_longitude")
    if lat is None or lon is None:
        frappe.throw(_("Branch latitude and longitude are required when mobile attendance is enabled."))
    if not -90 <= flt(lat) <= 90:
        frappe.throw(_("Branch Latitude must be between -90 and 90."))
    if not -180 <= flt(lon) <= 180:
        frappe.throw(_("Branch Longitude must be between -180 and 180."))
    if flt(doc.get("custom_attendance_radius")) <= 0:
        frappe.throw(_("Attendance Radius must be greater than zero."))
    if flt(doc.get("custom_max_gps_accuracy")) <= 0:
        frappe.throw(_("Maximum GPS Accuracy must be greater than zero."))

