import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt
class HRMobileAttendanceSettings(Document):
    def validate(self):
        self.fast_location_timeout = cint(self.fast_location_timeout) or 5
        self.high_accuracy_timeout = cint(self.high_accuracy_timeout) or 12
        if flt(self.default_radius)<=0: frappe.throw(_("Default Radius must be greater than zero."))
        if flt(self.default_max_gps_accuracy)<=0: frappe.throw(_("Default Maximum GPS Accuracy must be greater than zero."))
        if cint(self.location_cache_seconds) < 0 or cint(self.location_cache_seconds) > 600: frappe.throw(_("Location cache must be between 0 and 600 seconds."))
        if cint(self.fast_location_timeout) < 2 or cint(self.fast_location_timeout) > 30: frappe.throw(_("Fast location timeout must be between 2 and 30 seconds."))
        if cint(self.high_accuracy_timeout) < 5 or cint(self.high_accuracy_timeout) > 60: frappe.throw(_("High accuracy timeout must be between 5 and 60 seconds."))
        if self.require_branch: self.allow_without_branch=0
