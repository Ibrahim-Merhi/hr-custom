import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
class HRMobileAttendanceSettings(Document):
    def validate(self):
        if flt(self.default_radius)<=0: frappe.throw(_("Default Radius must be greater than zero."))
        if flt(self.default_max_gps_accuracy)<=0: frappe.throw(_("Default Maximum GPS Accuracy must be greater than zero."))
        if self.require_shift: self.allow_without_shift=0
        if self.require_branch: self.allow_without_branch=0
