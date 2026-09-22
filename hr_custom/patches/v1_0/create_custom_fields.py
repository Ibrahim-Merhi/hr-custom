import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


FIELDS = {
    "Employment Type": [
        dict(fieldname="custom_leave_calculation_mode", label="Leave Calculation Mode", fieldtype="Select", options="Days\nHours\nBoth", default="Days", reqd=1, insert_after="employee_type_name"),
        dict(fieldname="custom_weekly_work_schedule", label="Weekly Work Schedule", fieldtype="Link", options="Weekly Work Schedule", insert_after="custom_leave_calculation_mode"),
        dict(fieldname="custom_weekly_working_hours", label="Legacy Weekly Working Hours", fieldtype="Table", options="Employment Type Working Hours", insert_after="custom_weekly_work_schedule", depends_on="eval:doc.custom_leave_calculation_mode != 'Days' && !doc.custom_weekly_work_schedule", description="Existing embedded schedule. Prefer the reusable Weekly Work Schedule master."),
    ],
    "Employee": [
        dict(fieldname="custom_work_schedule_section", label="Work Schedule", fieldtype="Section Break", insert_after="employment_type", depends_on="eval:doc.employment_type", collapsible=1, description="Assign the reusable weekly schedule that defines working days and hours."),
        dict(fieldname="custom_weekly_work_schedule", label="Weekly Work Schedule", fieldtype="Link", options="Weekly Work Schedule", insert_after="custom_work_schedule_section", description="Used for working hours, hourly leave and return-to-work calculations."),
        dict(fieldname="custom_use_custom_work_schedule", label="Use Employee-Specific Work Schedule", fieldtype="Check", default="0", insert_after="custom_weekly_work_schedule", description="Enable only when this employee works different hours from the assigned Employment Type schedule."),
        dict(fieldname="custom_weekly_working_hours", label="Employee-Specific Working Hours", fieldtype="Table", options="Employee Working Hours", insert_after="custom_use_custom_work_schedule", depends_on="eval:doc.custom_use_custom_work_schedule", description="Set the required hours and optional work period for each working day."),
        dict(fieldname="custom_arabic_name_column", label="Arabic Name", fieldtype="Column Break", insert_after="employee_name"),
        dict(fieldname="custom_first_name_ar", label="First Name (Arabic)", fieldtype="Data", translatable=0, insert_after="custom_arabic_name_column"),
        dict(fieldname="custom_middle_name_ar", label="Middle Name (Arabic)", fieldtype="Data", translatable=0, insert_after="custom_first_name_ar"),
        dict(fieldname="custom_last_name_ar", label="Last Name (Arabic)", fieldtype="Data", translatable=0, insert_after="custom_middle_name_ar"),
        dict(fieldname="custom_employee_name_ar", label="Full Name (Arabic)", fieldtype="Data", translatable=0, read_only=1, in_standard_filter=1, insert_after="custom_last_name_ar"),
        dict(fieldname="custom_bilingual_name_section", label="Legacy Bilingual Employee Name", fieldtype="Section Break", insert_after="custom_employee_name_ar", hidden=1),
        dict(fieldname="custom_employee_name_en", label="Employee Name (English)", fieldtype="Data", translatable=0, insert_after="custom_bilingual_name_section", hidden=1),
        dict(fieldname="custom_name_column", fieldtype="Column Break", insert_after="custom_employee_name_en", hidden=1),
        dict(fieldname="custom_name_translation_source", label="Name Conversion Source", fieldtype="Select", options="\nSuggested from Arabic\nSuggested from English\nEntered by User\nCorrected by User", read_only=1, insert_after="custom_name_column", hidden=1),
        dict(fieldname="custom_name_translation_reviewed", label="Name Reviewed by User", fieldtype="Check", default="0", insert_after="custom_name_translation_source", hidden=1),
        dict(fieldname="custom_name_translation_locked", label="Protect User Correction", fieldtype="Check", default="0", insert_after="custom_name_translation_reviewed", hidden=1),
        dict(fieldname="custom_name_translation_notes", label="Name Translation Notes", fieldtype="Small Text", insert_after="custom_name_translation_locked", hidden=1),
        dict(fieldname="custom_personal_information_section", label="Personal Information", fieldtype="Section Break", insert_after="custom_name_translation_notes"),
        dict(fieldname="custom_personal_information_column", fieldtype="Column Break", insert_after="custom_personal_information_section"),
        dict(fieldname="custom_column_break_y2e93", fieldtype="Column Break", insert_after="image"),
        dict(fieldname="custom_leave_approval_section", label="Leave Approval", fieldtype="Section Break", insert_after="custom_personal_information_column", collapsible=1),
        dict(fieldname="custom_default_mobile_leave_type", label="Default Self-Service Leave Type", fieldtype="Link", options="Leave Type", insert_after="custom_leave_approval_section", hidden=1),
        dict(fieldname="custom_leave_calculation_mode_override", label="Leave Calculation Mode", fieldtype="Select", options="\nDays\nHours\nBoth", insert_after="custom_default_mobile_leave_type", description="Optional employee-specific override. Leave blank to inherit from Employment Type; employees without an Employment Type default to Days."),
        dict(fieldname="custom_leave_approvers", label="Leave Approvers", fieldtype="Table", options="Employee Leave Approver", insert_after="custom_default_mobile_leave_type", description="The first enabled row is the primary HRMS approver. All enabled approvers are notified."),
        dict(fieldname="custom_mobile_attendance_policy", label="Mobile Attendance Policy", fieldtype="Section Break", insert_after="custom_leave_approvers", collapsible=1),
        dict(fieldname="custom_location_not_required", label="Location Not Required", fieldtype="Check", default="0", insert_after="custom_mobile_attendance_policy", description="Allows this employee to clock in and out without GPS even when geolocation is required globally."),
        dict(fieldname="custom_attendance_branches", label="Allowed Clock-in Branches", fieldtype="Table", options="Employee Attendance Branch", insert_after="custom_location_not_required", description="Branches where this employee may clock in or out. If empty, the employee's main Branch is used."),
        dict(fieldname="custom_leave_balances_tab", label="Leave Balances", fieldtype="Section Break", insert_after="holiday_list", collapsible=1),
        dict(fieldname="custom_leave_balances_html", label="Leave Balances", fieldtype="HTML", insert_after="custom_leave_balances_tab"),
        dict(fieldname="custom_attendance_log_tab", label="Attendance Log", fieldtype="Section Break", insert_after="custom_leave_balances_html", collapsible=1),
        dict(fieldname="custom_attendance_log_html", label="Attendance Log", fieldtype="HTML", insert_after="custom_attendance_log_tab"),
        dict(fieldname="custom_column_break_ikfre", fieldtype="Column Break", insert_after="grade"),
    ],
    "Leave Type": [
        dict(fieldname="custom_leave_unit", label="Leave Unit", fieldtype="Select", options="Days\nHours", default="Days", reqd=1, insert_after="leave_type_name"),
        dict(fieldname="custom_legacy_leave_type_code", label="Legacy Leave Type Code", fieldtype="Data", unique=1, insert_after="custom_leave_unit", description="Code used to resolve leave types during legacy allowance migration."),
    ],
    "Leave Application": [
        dict(fieldname="custom_approval_workflow_section", label="Employee Approval Workflow", fieldtype="Section Break", insert_after="description", collapsible=1),
        dict(fieldname="custom_approval_stage", label="Approval Stage", fieldtype="Select", options="\nPending Approver Approval\nPending HR Approval\nApproved\nRejected", read_only=1, allow_on_submit=1, in_list_view=1, insert_after="custom_approval_workflow_section"),
        dict(fieldname="custom_current_approver", label="Current Approver", fieldtype="Link", options="User", read_only=1, allow_on_submit=1, insert_after="custom_approval_stage"),
        dict(fieldname="custom_approval_steps", label="Approval Steps", fieldtype="Table", options="Leave Application Approval Step", read_only=1, allow_on_submit=1, insert_after="custom_current_approver"),
        dict(fieldname="custom_hourly_leave_section", label="Hourly Leave", fieldtype="Section Break", insert_after="total_leave_days", depends_on="eval:doc.custom_leave_unit == 'Hours'"),
        dict(fieldname="custom_leave_unit", label="Leave Unit", fieldtype="Data", read_only=1, insert_after="custom_hourly_leave_section"),
        dict(fieldname="custom_leave_duration", label="Leave Duration", fieldtype="Select", options="Full Scheduled Hours\nPartial Hours", default="Full Scheduled Hours", insert_after="custom_leave_unit", depends_on="eval:doc.custom_leave_unit == 'Hours'"),
        dict(fieldname="custom_partial_hours", label="Requested Hours", fieldtype="Float", precision=2, insert_after="custom_leave_duration", depends_on="eval:doc.custom_leave_unit == 'Hours' && doc.custom_leave_duration == 'Partial Hours'"),
        dict(fieldname="custom_hourly_totals_column", fieldtype="Column Break", insert_after="custom_partial_hours"),
        dict(fieldname="custom_scheduled_hours", label="Scheduled Hours", fieldtype="Float", precision=2, read_only=1, insert_after="custom_hourly_totals_column", depends_on="eval:doc.custom_leave_unit == 'Hours'"),
        dict(fieldname="custom_leave_hours", label="Leave Hours", fieldtype="Float", precision=2, read_only=1, insert_after="custom_scheduled_hours", depends_on="eval:doc.custom_leave_unit == 'Hours'"),
        dict(fieldname="custom_hour_balance_before", label="Available Hour Balance", fieldtype="Float", precision=2, read_only=1, insert_after="custom_leave_hours", depends_on="eval:doc.custom_leave_unit == 'Hours'"),
        dict(fieldname="custom_hour_balance_after", label="Balance After Leave", fieldtype="Float", precision=2, read_only=1, insert_after="custom_hour_balance_before", depends_on="eval:doc.custom_leave_unit == 'Hours'"),
        dict(fieldname="custom_leave_hour_details", label="Leave Hours Breakdown", fieldtype="Table", options="Leave Hour Detail", read_only=1, insert_after="custom_hour_balance_after", depends_on="eval:doc.custom_leave_unit == 'Hours'"),
        dict(fieldname="custom_legacy_leave_section", label="Legacy Leave Information", fieldtype="Section Break", collapsible=1, insert_after="custom_leave_hour_details"),
        dict(fieldname="custom_return_to_work_date", label="Return to Work Date", fieldtype="Date", insert_after="custom_legacy_leave_section"),
        dict(fieldname="custom_legacy_voucher_number", label="Legacy Voucher Number", fieldtype="Data", insert_after="custom_return_to_work_date"),
        dict(fieldname="custom_legacy_balance_deducted", label="Legacy Balance Deducted", fieldtype="Float", precision=2, insert_after="custom_legacy_voucher_number"),
        dict(fieldname="custom_legacy_period_starting", label="Legacy Period Starting", fieldtype="Date", insert_after="custom_legacy_balance_deducted"),
        dict(fieldname="custom_is_migrated_record", label="Migrated Record", fieldtype="Check", default="0", insert_after="custom_legacy_period_starting"),
    ],
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
        dict(fieldname="custom_correction_request", label="Correction Request", fieldtype="Link", options="Attendance Correction Request", insert_after="custom_validation_message"),
    ],
    "Attendance": [
        dict(fieldname="custom_attendance_branches_section", label="Clock-in Branches", fieldtype="Section Break", insert_after="out_time", collapsible=1),
        dict(fieldname="custom_check_in_branch", label="Check-in Branch", fieldtype="Link", options="Branch", read_only=1, in_list_view=1, insert_after="custom_attendance_branches_section"),
        dict(fieldname="custom_check_out_branch", label="Check-out Branch", fieldtype="Link", options="Branch", read_only=1, in_list_view=1, insert_after="custom_check_in_branch"),
    ],
    "Leave Allocation": [
        dict(fieldname="custom_yearly_leave_allocation", label="Yearly Leave Allocation", fieldtype="Link", options="Yearly Leave Allocation", read_only=1, insert_after="to_date"),
        dict(fieldname="custom_yearly_leave_allocation_detail", label="Yearly Allocation Detail", fieldtype="Data", read_only=1, hidden=1, insert_after="custom_yearly_leave_allocation"),
    ],
    "PWA Notification": [
        dict(fieldname="custom_archived", label="Archived by Employee", fieldtype="Check", default="0", hidden=1, insert_after="read"),
    ],
}


def execute():
    _recreate_employee_history_breaks()
    create_custom_fields(FIELDS, update=True)
    from hr_custom.setup.employee_layout import apply_employee_layout
    apply_employee_layout()
    _backfill_arabic_name_parts()
    for doctype in FIELDS:
        frappe.clear_cache(doctype=doctype)


def _recreate_employee_history_breaks():
    for fieldname in ("custom_leave_balances_tab", "custom_attendance_log_tab"):
        name = f"Employee-{fieldname}"
        fieldtype = frappe.db.get_value("Custom Field", name, "fieldtype")
        if fieldtype and fieldtype != "Section Break":
            frappe.delete_doc("Custom Field", name, ignore_permissions=True)


def _backfill_arabic_name_parts():
    rows = frappe.get_all("Employee", filters={"custom_employee_name_ar": ["is", "set"]}, fields=["name", "custom_employee_name_ar", "custom_first_name_ar", "custom_middle_name_ar", "custom_last_name_ar"])
    for row in rows:
        if row.custom_first_name_ar or row.custom_middle_name_ar or row.custom_last_name_ar:
            continue
        parts = row.custom_employee_name_ar.split()
        if not parts:
            continue
        frappe.db.set_value("Employee", row.name, {
            "custom_first_name_ar": parts[0],
            "custom_middle_name_ar": " ".join(parts[1:-1]) if len(parts) > 2 else "",
            "custom_last_name_ar": parts[-1] if len(parts) > 1 else "",
        }, update_modified=False)
