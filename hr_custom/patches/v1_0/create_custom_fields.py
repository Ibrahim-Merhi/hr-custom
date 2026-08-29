import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


FIELDS = {
    "Branch": [
        dict(fieldname="custom_attendance_location", label="Attendance Location", fieldtype="Section Break", insert_after="custom_company"),
        dict(fieldname="custom_enable_mobile_attendance", label="Enable Mobile Attendance", fieldtype="Check", default="0", insert_after="custom_attendance_location"),
        dict(fieldname="custom_branch_latitude", label="Branch Latitude", fieldtype="Float", precision="7", insert_after="custom_enable_mobile_attendance"),
        dict(fieldname="custom_branch_longitude", label="Branch Longitude", fieldtype="Float", precision="7", insert_after="custom_branch_latitude"),
        dict(fieldname="custom_attendance_radius", label="Attendance Radius (Meters)", fieldtype="Float", default="100", insert_after="custom_branch_longitude"),
        dict(fieldname="custom_max_gps_accuracy", label="Maximum GPS Accuracy (Meters)", fieldtype="Float", default="50", insert_after="custom_attendance_radius"),
        dict(fieldname="custom_allow_checkin_without_location", label="Allow Check In Without Location", fieldtype="Check", default="0", insert_after="custom_max_gps_accuracy"),
        dict(fieldname="custom_mobile_attendance_notes", label="Mobile Attendance Notes", fieldtype="Small Text", insert_after="custom_allow_checkin_without_location"),
    ],
    "Employee Checkin": [
        dict(fieldname="custom_mobile_attendance_audit", label="Mobile Attendance Audit", fieldtype="Section Break", insert_after="shift_actual_end"),
        dict(fieldname="custom_branch", label="Branch", fieldtype="Link", options="Branch", insert_after="custom_mobile_attendance_audit"),
        dict(fieldname="custom_latitude", label="Latitude", fieldtype="Float", precision="7", insert_after="custom_branch"),
        dict(fieldname="custom_longitude", label="Longitude", fieldtype="Float", precision="7", insert_after="custom_latitude"),
        dict(fieldname="custom_gps_accuracy", label="GPS Accuracy", fieldtype="Float", insert_after="custom_longitude"),
        dict(fieldname="custom_distance_from_branch", label="Distance From Branch", fieldtype="Float", insert_after="custom_gps_accuracy"),
        dict(fieldname="custom_checkin_source", label="Checkin Source", fieldtype="Select", options="\nMobile GPS\nDesk\nBiometric\nAPI\nManual HR", insert_after="custom_distance_from_branch"),
        dict(fieldname="custom_device_info", label="Device Info", fieldtype="Small Text", insert_after="custom_checkin_source"),
        dict(fieldname="custom_user_agent", label="User Agent", fieldtype="Small Text", insert_after="custom_device_info"),
        dict(fieldname="custom_ip_address", label="IP Address", fieldtype="Data", insert_after="custom_user_agent"),
        dict(fieldname="custom_server_timestamp", label="Server Timestamp", fieldtype="Datetime", insert_after="custom_ip_address"),
        dict(fieldname="custom_geofence_validated", label="Geofence Validated", fieldtype="Check", insert_after="custom_server_timestamp"),
        dict(fieldname="custom_validation_message", label="Validation Message", fieldtype="Small Text", insert_after="custom_geofence_validated"),
        dict(fieldname="custom_shift_type", label="Shift Type", fieldtype="Link", options="Shift Type", insert_after="custom_validation_message"),
        dict(fieldname="custom_is_late", label="Is Late", fieldtype="Check", insert_after="custom_shift_type"),
        dict(fieldname="custom_minutes_late", label="Minutes Late", fieldtype="Int", insert_after="custom_is_late"),
        dict(fieldname="custom_is_early_exit", label="Is Early Exit", fieldtype="Check", insert_after="custom_minutes_late"),
        dict(fieldname="custom_minutes_early", label="Minutes Early", fieldtype="Int", insert_after="custom_is_early_exit"),
        dict(fieldname="custom_correction_request", label="Correction Request", fieldtype="Link", options="Attendance Correction Request", insert_after="custom_minutes_early"),
    ],
}


def execute():
    create_custom_fields(FIELDS, update=True)
    frappe.clear_cache(doctype="Branch")
    frappe.clear_cache(doctype="Employee Checkin")

