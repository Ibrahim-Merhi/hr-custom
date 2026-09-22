import frappe
from frappe import _
from frappe.model.document import Document


class HRAnnouncement(Document):
    def validate(self):
        self.title = (self.title or "").strip()
        self.message = (self.message or "").strip()
        if not self.title or not self.message:
            frappe.throw(_("Announcement title and message are required."))
        if not self.all_employees and not any(self.get(field) for field in ("companies", "departments", "employment_types", "employees")):
            frappe.throw(_("Select All Employees or add at least one target filter."))

    def get_target_employees(self):
        filters = {"status": "Active", "user_id": ["not in", ["", None]]}
        if not self.all_employees:
            mappings = {
                "companies": ("company", "company"),
                "departments": ("department", "department"),
                "employment_types": ("employment_type", "employment_type"),
                "employees": ("name", "employee"),
            }
            for table_field, (employee_field, row_field) in mappings.items():
                values = list(dict.fromkeys(row.get(row_field) for row in self.get(table_field) if row.get(row_field)))
                if values:
                    filters[employee_field] = ["in", values]
        return frappe.get_all("Employee", filters=filters, fields=["name", "employee_name", "user_id"], order_by="employee_name asc")

    def on_submit(self):
        recipients = self.get_target_employees()
        if not recipients:
            frappe.throw(_("No active employees with user accounts match the selected targets."))
        for employee in recipients:
            key = {"to_user": employee.user_id, "reference_document_type": self.doctype, "reference_document_name": self.name}
            if frappe.db.exists("PWA Notification", key):
                continue
            notification = frappe.new_doc("PWA Notification")
            notification.from_user = frappe.session.user
            notification.to_user = employee.user_id
            # The relay uses the reference DocType as the push title. Keeping
            # these on separate lines produces: HR Announcement / title / message.
            notification.message = f"{self.title}\n{self.message}"
            notification.reference_document_type = self.doctype
            notification.reference_document_name = self.name
            notification.insert(ignore_permissions=True)
        self.db_set("recipient_count", len(recipients), update_modified=False)
