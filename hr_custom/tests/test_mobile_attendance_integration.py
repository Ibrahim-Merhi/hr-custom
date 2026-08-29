from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee
from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log

from hr_custom.api import mobile_attendance
from hr_custom.attendance.exceptions import scan_recent_checkins
from hr_custom.attendance.geofence import get_distance_in_meters, validate_coordinates
from hr_custom.attendance.shift import timing_flags


class TestMobileAttendanceIntegration(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = "mobile.attendance.test@example.com"
        cls.employee = make_employee(cls.user, company="_Test Company")
        if not frappe.db.exists("Branch", "_Test Mobile Branch"):
            frappe.get_doc({"doctype":"Branch","branch":"_Test Mobile Branch"}).insert(ignore_permissions=True)
        frappe.db.set_value("Branch", "_Test Mobile Branch", {"custom_enable_mobile_attendance":1,"custom_branch_latitude":24.7136,"custom_branch_longitude":46.6753,"custom_attendance_radius":200,"custom_max_gps_accuracy":50})
        frappe.db.set_value("Employee", cls.employee, {"branch":"_Test Mobile Branch","status":"Active","user_id":cls.user})
        settings=frappe.get_single("HR Mobile Attendance Settings")
        settings.update({"enable_mobile_attendance":1,"require_geolocation":1,"require_branch":1,"allow_without_branch":0,"require_shift":0,"allow_without_shift":1,"enforce_checkin_window":0,"require_registered_device":0})
        settings.save(ignore_permissions=True)

    def setUp(self):
        frappe.set_user(self.user)
        frappe.db.delete("Employee Checkin", {"employee":self.employee})

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_01_active_employee_mapping(self):
        self.assertEqual(mobile_attendance._employee_for_user().name,self.employee)
    def test_02_inactive_employee_rejected(self):
        frappe.db.set_value("Employee",self.employee,"status","Inactive")
        with self.assertRaises(frappe.PermissionError): mobile_attendance._employee_for_user()
        frappe.db.set_value("Employee",self.employee,"status","Active")
    def test_03_user_without_employee_rejected(self):
        frappe.set_user("Administrator")
        with self.assertRaises(frappe.PermissionError): mobile_attendance._employee_for_user()
    def test_04_browser_employee_is_not_an_api_argument(self):
        self.assertNotIn("employee", __import__("inspect").signature(mobile_attendance.submit_checkin).parameters)
    def test_05_disabled_branch_rejected(self):
        frappe.db.set_value("Branch","_Test Mobile Branch","custom_enable_mobile_attendance",0)
        with self.assertRaises(frappe.ValidationError): mobile_attendance._branch(mobile_attendance._employee_for_user(),mobile_attendance._settings())
        frappe.db.set_value("Branch","_Test Mobile Branch","custom_enable_mobile_attendance",1)
    def test_06_missing_branch_rejected(self):
        frappe.db.set_value("Employee",self.employee,"branch",None)
        with self.assertRaises(frappe.ValidationError): mobile_attendance._branch(mobile_attendance._employee_for_user(),mobile_attendance._settings())
        frappe.db.set_value("Employee",self.employee,"branch","_Test Mobile Branch")
    def test_07_missing_coordinates_rejected(self):
        frappe.db.set_value("Branch","_Test Mobile Branch","custom_branch_latitude",None)
        with self.assertRaises(frappe.ValidationError): mobile_attendance._branch(mobile_attendance._employee_for_user(),mobile_attendance._settings())
        frappe.db.set_value("Branch","_Test Mobile Branch","custom_branch_latitude",24.7136)
    def test_08_inside_radius(self):
        self.assertLess(get_distance_in_meters(24.7136,46.6753,24.7137,46.6753),200)
    def test_09_outside_radius_rejected(self):
        branch=mobile_attendance._branch(mobile_attendance._employee_for_user(),mobile_attendance._settings())
        with self.assertRaises(frappe.ValidationError): mobile_attendance._validate_location(branch,mobile_attendance._settings(),25,47,10)
    def test_10_poor_accuracy_rejected(self):
        branch=mobile_attendance._branch(mobile_attendance._employee_for_user(),mobile_attendance._settings())
        with self.assertRaises(frappe.ValidationError): mobile_attendance._validate_location(branch,mobile_attendance._settings(),24.7136,46.6753,100)
    def test_11_server_time_used(self):
        with patch("hr_custom.api.mobile_attendance.now_datetime",return_value=datetime(2024,1,1,8)):
            with patch.object(mobile_attendance,"resolve_shift",return_value=None):
                result=mobile_attendance.submit_checkin(24.7136,46.6753,5)
                self.assertEqual(frappe.db.get_value("Employee Checkin",result["name"],"time"),datetime(2024,1,1,8))
    def test_12_first_event_is_in(self):
        self.assertEqual(mobile_attendance.submit_checkin(24.7136,46.6753,5)["action"],"IN")
    def test_13_second_event_is_out(self):
        first=now_datetime()-timedelta(minutes=1)
        frappe.get_doc({"doctype":"Employee Checkin","employee":self.employee,"time":first,"log_type":"IN"}).insert(ignore_permissions=True)
        self.assertEqual(mobile_attendance.submit_checkin(24.7136,46.6753,5)["action"],"OUT")
    def test_14_rapid_duplicate_rejected(self):
        frappe.get_doc({"doctype":"Employee Checkin","employee":self.employee,"time":now_datetime(),"log_type":"IN"}).insert(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError): mobile_attendance.submit_checkin(24.7136,46.6753,5)
    def test_15_standard_checkin_created(self):
        result=mobile_attendance.submit_checkin(24.7136,46.6753,5)
        self.assertTrue(frappe.db.exists("Employee Checkin",result["name"]))
    def test_16_mobile_source_stored(self):
        result=mobile_attendance.submit_checkin(24.7136,46.6753,5)
        self.assertEqual(frappe.db.get_value("Employee Checkin",result["name"],"custom_checkin_source"),"Mobile GPS")
    def test_17_geofence_stored(self):
        result=mobile_attendance.submit_checkin(24.7136,46.6753,5)
        self.assertEqual(frappe.db.get_value("Employee Checkin",result["name"],"custom_geofence_validated"),1)
    def test_18_late_calculation(self):
        shift=frappe._dict(start=datetime(2024,1,1,8),end=datetime(2024,1,1,16),enable_late=1,late_grace=10,enable_early=1,early_grace=10)
        self.assertEqual(timing_flags(shift,datetime(2024,1,1,8,14),"IN"),{"is_late":1,"minutes_late":14,"is_early_exit":0,"minutes_early":0})
    def test_19_early_exit_calculation(self):
        shift=frappe._dict(start=datetime(2024,1,1,8),end=datetime(2024,1,1,16),enable_late=1,late_grace=10,enable_early=1,early_grace=10)
        self.assertEqual(timing_flags(shift,datetime(2024,1,1,15,35),"OUT")["minutes_early"],25)
    def test_20_same_coordinates_zero(self):
        self.assertAlmostEqual(get_distance_in_meters(1,2,1,2),0)
    def test_21_known_hundred_meters(self):
        self.assertTrue(95<get_distance_in_meters(0,0,0,.0009)<105)
    def test_22_invalid_latitude(self):
        with self.assertRaises(ValueError): validate_coordinates(91,0)
    def test_23_invalid_longitude(self):
        with self.assertRaises(ValueError): validate_coordinates(0,181)
    def test_24_missing_checkout_exception_idempotent(self):
        yesterday=datetime.combine(frappe.utils.add_days(nowdate(),-1),datetime.min.time())+timedelta(hours=8)
        frappe.get_doc({"doctype":"Employee Checkin","employee":self.employee,"time":yesterday,"log_type":"IN","custom_branch":"_Test Mobile Branch"}).insert(ignore_permissions=True)
        scan_recent_checkins(); scan_recent_checkins()
        self.assertEqual(frappe.db.count("Attendance Exception",{"employee":self.employee,"attendance_date":yesterday.date(),"exception_type":"Missing Check Out","status":"Open"}),1)
    def test_25_correction_employee_scope(self):
        doc=frappe.get_doc({"doctype":"Attendance Correction Request","employee":self.employee,"attendance_date":nowdate(),"request_type":"Missing Check In","requested_check_in_time":now_datetime(),"reason":"Test"})
        doc.insert(); self.assertEqual(doc.employee,self.employee)
    def test_26_duplicate_attendance_prevented(self):
        frappe.get_doc({"doctype":"Attendance","employee":self.employee,"attendance_date":nowdate(),"status":"Present","company":"_Test Company"}).insert(ignore_permissions=True)
        duplicate=frappe.get_doc({"doctype":"Attendance","employee":self.employee,"attendance_date":nowdate(),"status":"Present","company":"_Test Company"})
        with self.assertRaises(frappe.ValidationError): duplicate.insert(ignore_permissions=True)
