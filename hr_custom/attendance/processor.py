import frappe
def process_pending_attendance():
    from hrms.hr.doctype.shift_type.shift_type import process_auto_attendance_for_all_shifts
    process_auto_attendance_for_all_shifts()
def finalize_previous_day():
    process_pending_attendance()
