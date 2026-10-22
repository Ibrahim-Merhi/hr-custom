from datetime import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hr_custom.hr_custom.doctype.weekly_work_schedule.weekly_work_schedule import assign_employees
from hr_custom.hr_custom.report.weekly_employee_hours.weekly_employee_hours import _worked_hours
from hr_custom.services.employee_name import apply_bilingual_name, arabic_to_english, english_to_arabic
from hr_custom.services.work_schedule import get_employee_schedule, get_scheduled_period
from hr_custom.services.work_schedule_profile import get_profile, save_profile


class TestWorkScheduleAndNames(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def test_reusable_schedule_assignment_and_employee_override(self):
        # This test owns only the HR schedule. Marking the fixture as an internal
        # payroll identity bypasses the accounting app's unrelated company table.
        employee_kwargs = {}
        if frappe.get_meta("Employee").has_field("custom_is_payroll_identity"):
            employee_kwargs["custom_is_payroll_identity"] = 1
        employee = make_employee(
            "weekly.schedule.test@example.com", company="_Test Company", **employee_kwargs
        )
        schedule = frappe.get_doc({
            "doctype": "Weekly Work Schedule", "schedule_name": "_Test Reusable Week",
            "working_hours": [
                {"day_of_week": "Monday", "working_hours": 8, "enabled": 1},
                {"day_of_week": "Tuesday", "working_hours": 6.5, "enabled": 1},
            ],
        }).insert()
        self.assertEqual(schedule.total_weekly_hours, 14.5)
        self.assertEqual(assign_employees(schedule.name, [employee])["assigned"], 1)
        values, source = get_employee_schedule(employee)
        self.assertEqual(source, "Weekly Work Schedule")
        self.assertEqual(values["Tuesday"], 6.5)

        employee_doc = frappe.get_doc("Employee", employee)
        employee_doc.custom_use_custom_work_schedule = 1
        employee_doc.append("custom_weekly_working_hours", {
            "day_of_week": "Tuesday", "working_hours": 5,
            "from_time": "09:30:00", "to_time": "14:30:00", "enabled": 1,
        })
        employee_doc.save()
        values, source = get_employee_schedule(employee)
        self.assertEqual(source, "Employee")
        self.assertEqual(values["Tuesday"], 5)
        period = get_scheduled_period(employee, "2027-01-05")
        self.assertEqual(period["source"], "Employee")
        self.assertEqual(period["working_hours"], 5)
        self.assertEqual(str(period["from_time"]), "9:30:00")
        self.assertEqual(str(period["to_time"]), "14:30:00")

    def test_employee_schedule_revisions_preserve_effective_history(self):
        employee_kwargs = {}
        if frappe.get_meta("Employee").has_field("custom_is_payroll_identity"):
            employee_kwargs["custom_is_payroll_identity"] = 1
        employee = make_employee(
            "schedule.history.test@example.com", company="_Test Company", **employee_kwargs
        )
        first = [
            {
                "day_of_week": day,
                "working_hours": 8,
                "from_time": "08:00:00",
                "to_time": "16:00:00",
                "enabled": 1,
            }
            for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
        ]
        save_profile({
            "employee": employee,
            "effective_from": "2027-01-01",
            "action_date": "2027-01-01",
            "change_summary": "Initial employee schedule",
            "rows": first,
        })
        changed = [dict(row) for row in first]
        friday = next(row for row in changed if row["day_of_week"] == "Friday")
        friday.update({"working_hours": 9, "from_time": "09:00:00", "to_time": "18:00:00"})
        save_profile({
            "employee": employee,
            "effective_from": "2027-02-01",
            "action_date": "2027-01-25",
            "change_summary": "Friday shift changed",
            "rows": changed,
        })

        profile = get_profile(employee)
        self.assertEqual(profile["revision_count"], 2)
        self.assertIn("Friday", profile["revisions"][0].change_summary)
        self.assertEqual(get_scheduled_period(employee, "2027-01-08")["working_hours"], 8)
        current = get_scheduled_period(employee, "2027-02-05")
        self.assertEqual(current["working_hours"], 9)
        self.assertEqual(str(current["from_time"]), "9:00:00")
        self.assertEqual(get_employee_schedule(employee, "2027-01-08")[1], "Employee Schedule History")

    def test_bilingual_name_parts_build_full_names(self):
        self.assertTrue(arabic_to_english("محمد علي"))
        self.assertTrue(english_to_arabic("Mohammed Ali"))
        doc = frappe._dict({
            "custom_first_name_ar": "محمد", "custom_middle_name_ar": "أحمد",
            "custom_last_name_ar": "علي", "custom_employee_name_ar": "",
            "custom_employee_name_en": "", "employee_name": "Mohammed Ahmed Ali",
        })
        apply_bilingual_name(doc)
        self.assertEqual(doc.custom_employee_name_ar, "محمد أحمد علي")
        self.assertEqual(doc.custom_employee_name_en, "Mohammed Ahmed Ali")

    def test_checkin_pairs_and_incomplete_detection(self):
        complete = [
            frappe._dict(log_type="IN", time=datetime(2027, 1, 4, 8)),
            frappe._dict(log_type="OUT", time=datetime(2027, 1, 4, 12)),
            frappe._dict(log_type="IN", time=datetime(2027, 1, 4, 13)),
            frappe._dict(log_type="OUT", time=datetime(2027, 1, 4, 17, 30)),
        ]
        self.assertEqual(_worked_hours(complete), (8.5, 0))
        self.assertEqual(_worked_hours(complete[:-1]), (4.0, 1))
