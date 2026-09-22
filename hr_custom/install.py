def before_install():
    """Expose this app's modules to the first install model-sync pass."""
    import frappe

    frappe.cache.delete_value("app_modules")
    frappe.local.app_modules = None
    frappe.setup_module_map(include_all_apps=True)


def before_migrate():
    """Repair the malformed legacy custom_pr patch entry before patch loading."""
    import frappe

    bad_patch = "custom_pr.patches.v1_0.migrate_donor_representatives.execute"
    if "custom_pr" not in frappe.get_installed_apps() or frappe.db.get_value(
        "Patch Log", {"patch": bad_patch, "skipped": 0}
    ):
        return
    from custom_pr.patches.v1_0.migrate_donor_representatives import execute

    execute()
    frappe.get_doc({"doctype": "Patch Log", "patch": bad_patch}).insert(ignore_permissions=True)


def after_sync():
    from hr_custom.patches.v1_0.create_custom_fields import execute
    from hr_custom.setup.workspace import ensure_hr_workspace_section
    execute(); ensure_hr_workspace_section()
def after_migrate():
    from hr_custom.patches.v1_0.create_custom_fields import execute
    from hr_custom.setup.workspace import ensure_hr_workspace_section
    from hr_custom.api.portal_auth import upgrade_legacy_portal_passwords
    execute(); ensure_hr_workspace_section(); upgrade_legacy_portal_passwords()
def before_uninstall():
    from hr_custom.setup.workspace import remove_hr_workspace_section
    remove_hr_workspace_section()
