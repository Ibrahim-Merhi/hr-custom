def after_install():
    from hr_custom.patches.v1_0.create_custom_fields import execute
    execute()


def after_migrate():
    from hr_custom.patches.v1_0.create_custom_fields import execute
    execute()

