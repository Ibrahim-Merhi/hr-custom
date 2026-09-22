def before_install():
    """Expose this app's modules to the first install model-sync pass."""
    import frappe

    frappe.cache.delete_value("app_modules")
    frappe.local.app_modules = None
    frappe.setup_module_map(include_all_apps=True)


def after_sync():
    from hr_custom.patches.v1_0.create_custom_fields import execute
    from hr_custom.setup.workspace import ensure_hr_workspace_section
    execute(); ensure_hr_workspace_section()
def after_migrate():
    from hr_custom.patches.v1_0.create_custom_fields import execute
    from hr_custom.setup.workspace import ensure_hr_workspace_section
    execute(); ensure_hr_workspace_section()
def before_uninstall():
    from hr_custom.setup.workspace import remove_hr_workspace_section
    remove_hr_workspace_section()
