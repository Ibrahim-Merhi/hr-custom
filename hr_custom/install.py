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
