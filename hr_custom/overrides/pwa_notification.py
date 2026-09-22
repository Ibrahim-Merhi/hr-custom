import frappe

from hrms.hr.doctype.pwa_notification.pwa_notification import PWANotification


class CustomPWANotification(PWANotification):
    def get_notification_link(self):
        if self.reference_document_type == "HR Announcement":
            # A same-origin relative URL lets iOS reopen the installed PWA and
            # retain its authenticated cookie instead of launching HTTP Safari.
            return "/attendance"
        return super().get_notification_link()

    def send_push_notification(self):
        if self.reference_document_type != "HR Announcement":
            return super().send_push_notification()
        try:
            from frappe.push_notification import PushNotification

            announcement = frappe.get_doc("HR Announcement", self.reference_document_name)
            push_notification = PushNotification("hrms")
            if push_notification.is_enabled():
                push_notification.send_notification_to_user(
                    self.to_user,
                    f"HR Announcement · {announcement.title}",
                    announcement.message,
                    link="/attendance",
                    icon=f"{frappe.utils.get_url()}/assets/hr_custom/images/attendance-icon-512.png",
                )
        except ImportError:
            pass
        except Exception:
            self.log_error(f"Error sending announcement push notification: {self.name}")

    @staticmethod
    def get_url():
        from frappe.utils import get_url
        return get_url()
