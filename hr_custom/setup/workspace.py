import json

import frappe

PREFIX = "hr_custom_"
DASHBOARD_COMPANY = "Itihad"
GROUPS = [
    ("Employee Communications", [
        ("HR Announcement", "DocType", "HR Announcement", "Green"),
    ]),
    ("Work Schedules & Hourly Leave", [
        ("Weekly Work Schedule", "DocType", "Weekly Work Schedule", "Blue"),
        ("Weekly Employee Hours", "Report", "Weekly Employee Hours", "Blue"),
        ("Hourly Leave Balance", "Report", "Hourly Leave Balance", "Blue"),
    ]),
    ("Leave Management", [
        ("Yearly Leave Allocation", "DocType", "Yearly Leave Allocation", "Green"),
        ("Yearly Leave Allocation Summary", "Report", "Yearly Leave Allocation Summary", "Blue"),
        ("Leave Allocation", "DocType", "Leave Allocation", "Grey"),
    ]),
    ("Attendance Operations", [
        ("GPS Attendance", "URL", "/attendance", "Green"),
        ("Attendance Correction Request", "DocType", "Attendance Correction Request", "Orange"),
        ("Attendance Exception", "DocType", "Attendance Exception", "Red"),
        ("Daily Attendance Overview", "Report", "Daily Attendance Overview", "Blue"),
        ("Mobile Checkin Audit", "Report", "Mobile Checkin Audit", "Grey"),
        ("Attendance Exceptions", "Report", "Attendance Exceptions", "Grey"),
        ("Abnormal Attendance Records", "Report", "Abnormal Attendance Records", "Orange"),
    ]),
    ("Attendance Configuration", [
        ("HR Mobile Attendance Settings", "DocType", "HR Mobile Attendance Settings", "Grey"),
        ("Employee Attendance Device", "DocType", "Employee Attendance Device", "Grey"),
    ]),
    ("Portal Access", [
        ("Employee Portal Credential", "DocType", "Employee Portal Credential", "Green"),
    ]),
]
LABELS = {item[0] for _, items in GROUPS for item in items} | {"Mobile Attendance", "HR Attendance Dashboard", "Daily Attendance Overview"}

CUSTOM_CARD_METHODS = {
    "HR Active Employees": "hr_custom.services.workspace_cards.active_employees",
    "HR Present Today": "hr_custom.services.workspace_cards.present_today",
    "HR Absent Today": "hr_custom.services.workspace_cards.absent_today",
    "HR On Leave Today": "hr_custom.services.workspace_cards.on_leave_today",
}

MANAGER_NUMBER_CARDS = (
    ("HR Active Employees", "Active Employees", "Employee", [["status", "=", "Active"]], []),
    ("HR Present Today", "Present Today", "Attendance", [["status", "=", "Present"], ["docstatus", "=", 1]], [["attendance_date", "=", "frappe.datetime.get_today()"]]),
    ("HR Absent Today", "Absent Today", "Attendance", [["status", "=", "Absent"], ["docstatus", "=", 1]], [["attendance_date", "=", "frappe.datetime.get_today()"]]),
    ("HR On Leave Today", "Employees on Leave Today", "Attendance", [["status", "=", "On Leave"], ["docstatus", "=", 1]], [["attendance_date", "=", "frappe.datetime.get_today()"]]),
    ("HR New Employees This Month", "New Employees This Month", "Employee", [], [["date_of_joining", ">=", "frappe.datetime.month_start()"], ["date_of_joining", "<=", "frappe.datetime.month_end()"]]),
    ("HR Employees Leaving Soon", "Employees Leaving Soon", "Employee", [["status", "=", "Active"]], [["relieving_date", ">=", "frappe.datetime.get_today()"], ["relieving_date", "<=", "frappe.datetime.add_days(frappe.datetime.get_today(), 30)"]]),
    ("HR Pending Leave Applications", "Pending Leave Applications", "Leave Application", [["status", "=", "Open"], ["docstatus", "=", 0]], []),
    ("HR Pending Expense Claims", "Pending Expense Claims", "Expense Claim", [["approval_status", "=", "Draft"], ["docstatus", "=", 0]], []),
)

MANAGER_CHARTS = (
    ("Employees by Branch", "Employees by Branch"),
    ("Employees by Department", "Department Wise Employee Count"),
    ("Monthly Attendance Trend", "Attendance Count"),
    ("Leave Distribution", "HR Leave Distribution"),
    ("Employee Joining and Leaving Trend", "Hiring vs Attrition Count"),
    ("Payroll by Month", "Outgoing Salary"),
    ("Salary Distribution by Branch or Cost Center", "Department Wise Salary(Last Month)"),
)

MANAGER_SHORTCUTS = (
    ("Employee", "DocType"), ("Attendance", "DocType"),
    ("Leave Application", "DocType"), ("Salary Slip", "DocType"),
    ("Payroll Entry", "DocType"), ("Shift Assignment", "DocType"),
    ("Employee Monthly Adjustment", "DocType"),
    ("Payroll Cost Center Allocation", "DocType"),
)

MANAGER_REPORTS = (
    ("Employee Attendance", "Report", "Daily Attendance Overview"),
    ("Monthly Attendance Sheet", "Report", "Monthly Attendance Sheet"),
    ("Employee Leave Balance", "Report", "Employee Leave Balance"),
    ("Payroll Register", "Report", "Salary Register"),
    ("Salary Register", "Report", "Salary Register"),
    ("Employee Working Branches", "Report", "Attendance Branch Report"),
    ("Employee Salary Accounts", "DocType", "Employee"),
    ("Payroll Cost-Center Allocation", "DocType", "Payroll Cost Center Allocation"),
    ("Employee Monthly Adjustments", "DocType", "Employee Monthly Adjustment"),
)


def ensure_hr_workspace_section():
    if not frappe.db.exists("Workspace", "HR"):
        return
    doc = frappe.get_doc("Workspace", "HR")
    content = [item for item in json.loads(doc.content or "[]") if not item.get("id", "").startswith(PREFIX)]
    shortcut_number = 0
    for group_number, (title, items) in enumerate(GROUPS):
        content.append({"id": f"{PREFIX}header_{group_number}", "type": "header", "data": {"text": f'<span class="h4"><b>{title}</b></span>', "col": 12}})
        for label, _, _, _ in items:
            content.append({"id": f"{PREFIX}shortcut_{shortcut_number}", "type": "shortcut", "data": {"shortcut_name": label, "col": 4}})
            shortcut_number += 1
        content.append({"id": f"{PREFIX}spacer_{group_number}", "type": "spacer", "data": {"col": 12}})
    doc.content = json.dumps(content, separators=(",", ":"))
    doc.set("shortcuts", [row.as_dict() for row in doc.shortcuts if row.label not in LABELS])
    for _, items in GROUPS:
        for label, kind, target, color in items:
            row = {"type": kind, "label": label, "color": color}
            if kind == "URL":
                row["url"] = target
            else:
                row["link_to"] = target
            if kind == "DocType":
                row["doc_view"] = "List"
            doc.append("shortcuts", row)
    _ensure_hr_manager_dashboard(doc)
    _save(doc)


def _ensure_hr_manager_dashboard(doc):
    card_names = _ensure_manager_number_cards()
    _ensure_leave_distribution_chart()
    chart_names = _ensure_manager_charts()
    content = json.loads(doc.content or "[]")
    dashboard = [{"id": f"{PREFIX}manager_header", "type": "header", "data": {"text": "<span class=\"h4\"><b>HR Manager Dashboard</b></span>", "col": 12}}]
    for index, (configured_name, *_rest) in enumerate(MANAGER_NUMBER_CARDS, 1):
        dashboard.append({"id": f"{PREFIX}manager_number_{index}", "type": "number_card", "data": {"number_card_name": card_names[configured_name], "col": 3}})
    dashboard.extend([
        {"id": f"{PREFIX}manager_spacer_1", "type": "spacer", "data": {"col": 12}},
        {"id": f"{PREFIX}manager_analytics_header", "type": "header", "data": {"text": "<span class=\"h4\"><b>HR Analytics</b></span>", "col": 12}},
    ])
    for index, chart_name in enumerate(chart_names, 1):
        dashboard.append({"id": f"{PREFIX}manager_chart_{index}", "type": "chart", "data": {"chart_name": chart_name, "col": 6}})
    dashboard.extend([
        {"id": f"{PREFIX}manager_spacer_2", "type": "spacer", "data": {"col": 12}},
        {"id": f"{PREFIX}manager_operations_header", "type": "header", "data": {"text": "<span class=\"h4\"><b>HR Operations</b></span>", "col": 12}},
    ])
    for index, (label, _link_type) in enumerate(MANAGER_SHORTCUTS, 1):
        dashboard.append({"id": f"{PREFIX}manager_shortcut_{index}", "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
    dashboard.extend([
        {"id": f"{PREFIX}manager_spacer_3", "type": "spacer", "data": {"col": 12}},
        {"id": f"{PREFIX}manager_reports_header", "type": "header", "data": {"text": "<span class=\"h4\"><b>HR Manager Reports</b></span>", "col": 12}},
        {"id": f"{PREFIX}manager_reports_card", "type": "card", "data": {"card_name": "HR Manager Reports", "col": 4}},
    ])
    doc.content = json.dumps(dashboard + content, separators=(",", ":"))

    managed_cards = set(card_names.values())
    doc.set("number_cards", [row.as_dict() for row in doc.number_cards if row.number_card_name not in managed_cards])
    for configured_name, label, *_rest in MANAGER_NUMBER_CARDS:
        doc.append("number_cards", {"number_card_name": card_names[configured_name], "label": label})

    managed_chart_names = {value for pair in MANAGER_CHARTS for value in pair}
    doc.set("charts", [row.as_dict() for row in doc.charts if row.chart_name not in managed_chart_names])
    for chart_name in chart_names:
        doc.append("charts", {"chart_name": chart_name, "label": chart_name})

    managed_shortcuts = {label for label, _link_type in MANAGER_SHORTCUTS}
    doc.set("shortcuts", [row.as_dict() for row in doc.shortcuts if row.label not in managed_shortcuts])
    for label, link_type in MANAGER_SHORTCUTS:
        if frappe.db.exists(link_type, label):
            doc.append("shortcuts", {"label": label, "type": link_type, "link_to": label, "doc_view": "List"})

    managed_reports = {target for _label, _link_type, target in MANAGER_REPORTS} | {"Employee Analytics", "Employee Information"}
    managed_report_labels = {label for label, _link_type, _target in MANAGER_REPORTS} | {"Employee Analytics", "Employee Information"}
    links = [row.as_dict() for row in doc.links if not ((row.type == "Card Break" and row.label == "HR Manager Reports") or (row.type == "Link" and (row.link_to in managed_reports or row.label in managed_report_labels)))]
    links.append({"type": "Card Break", "label": "HR Manager Reports"})
    for label, link_type, target in MANAGER_REPORTS:
        if frappe.db.exists(link_type, target):
            row = {"type": "Link", "label": label, "link_type": link_type, "link_to": target}
            if link_type == "Report":
                row["is_query_report"] = 1
            links.append(row)
    doc.set("links", links)


def _ensure_manager_charts():
    """Install manager-facing copies with stable, descriptive dashboard titles."""
    installed = []
    for chart_name, source_name in MANAGER_CHARTS:
        if chart_name == source_name:
            if frappe.db.exists("Dashboard Chart", chart_name):
                chart = frappe.get_doc("Dashboard Chart", chart_name)
                values = chart.as_dict(no_nulls=False)
                _pin_chart_company(values)
                frappe.db.set_value(
                    "Dashboard Chart", chart_name,
                    {"filters_json": values["filters_json"], "dynamic_filters_json": values["dynamic_filters_json"]},
                    update_modified=False,
                )
                installed.append(chart_name)
            continue
        if not frappe.db.exists("Dashboard Chart", source_name):
            continue
        source = frappe.get_doc("Dashboard Chart", source_name)
        values = source.as_dict(no_nulls=False)
        for key in ("name", "owner", "creation", "modified", "modified_by", "docstatus", "idx", "doctype", "is_standard", "last_synced_on"):
            values.pop(key, None)
        _pin_chart_company(values)
        values.update({"chart_name": chart_name, "module": "HR Custom", "is_standard": 0})
        if frappe.db.exists("Dashboard Chart", chart_name):
            chart = frappe.get_doc("Dashboard Chart", chart_name)
            chart.update(values)
            chart.save(ignore_permissions=True)
        else:
            chart = frappe.get_doc({"doctype": "Dashboard Chart", **values})
            chart.name = chart_name
            chart.insert(ignore_permissions=True)
        installed.append(chart_name)
    return installed


def _pin_chart_company(values):
    """Use the HR operating company instead of the unrelated site default."""
    dynamic = json.loads(values.get("dynamic_filters_json") or "[]")
    if isinstance(dynamic, list):
        dynamic = [row for row in dynamic if len(row) < 2 or row[1] != "company"]
    elif isinstance(dynamic, dict):
        dynamic.pop("company", None)
    values["dynamic_filters_json"] = json.dumps(dynamic)

    filters = json.loads(values.get("filters_json") or "[]")
    if isinstance(filters, list) and values.get("document_type"):
        filters = [row for row in filters if len(row) < 2 or row[1] != "company"]
        filters.append([values["document_type"], "company", "=", DASHBOARD_COMPANY, False])
    elif isinstance(filters, dict):
        filters["company"] = DASHBOARD_COMPANY
    values["filters_json"] = json.dumps(filters)


def _ensure_manager_number_cards():
    card_names = {}
    company_filter = ["company", "=", DASHBOARD_COMPANY]
    for configured_name, label, document_type, filters, dynamic_filters in MANAGER_NUMBER_CARDS:
        values = {
            "label": label, "type": "Document Type", "document_type": document_type, "function": "Count",
            "filters_json": json.dumps([[document_type, *company_filter, False], *[[document_type, *item, False] for item in filters]]),
            "dynamic_filters_json": json.dumps([[document_type, *item] for item in dynamic_filters]),
            "is_public": 1, "is_standard": 0, "module": "HR Custom", "show_percentage_stats": 0,
        }
        if configured_name in CUSTOM_CARD_METHODS:
            values.update({
                "type": "Custom",
                "method": CUSTOM_CARD_METHODS[configured_name],
                "filters_json": "[]",
                "dynamic_filters_json": "[]",
            })
        existing_name = frappe.db.get_value("Number Card", {"label": label, "module": ["in", ["HR Custom", "Accounting Custom"]]}, "name")
        if existing_name:
            card = frappe.get_doc("Number Card", existing_name)
            card.update(values)
            card.save(ignore_permissions=True)
        else:
            card = frappe.get_doc({"doctype": "Number Card", **values})
            card.name = configured_name
            card.insert(ignore_permissions=True)
        card_names[configured_name] = card.name
    return card_names


def _ensure_leave_distribution_chart():
    name = "HR Leave Distribution"
    values = {
        "chart_name": name, "chart_type": "Group By", "document_type": "Leave Application",
        "filters_json": json.dumps([["Leave Application", "docstatus", "=", 1, False]]),
        "dynamic_filters_json": json.dumps([["Leave Application", "company", "=", "frappe.defaults.get_user_default(\"Company\")"]]),
        "group_by_based_on": "leave_type", "group_by_type": "Count", "is_public": 1,
        "is_standard": 0, "module": "HR Custom", "timeseries": 0, "type": "Donut", "use_report_chart": 0,
    }
    if frappe.db.exists("Dashboard Chart", name):
        chart = frappe.get_doc("Dashboard Chart", name)
        chart.update(values)
        chart.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "Dashboard Chart", "name": name, **values}).insert(ignore_permissions=True)


def remove_hr_workspace_section():
    if not frappe.db.exists("Workspace", "HR"):
        return
    doc = frappe.get_doc("Workspace", "HR")
    doc.content = json.dumps([item for item in json.loads(doc.content or "[]") if not item.get("id", "").startswith(PREFIX)], separators=(",", ":"))
    doc.set("shortcuts", [row.as_dict() for row in doc.shortcuts if row.label not in LABELS])
    _save(doc)


def _save(doc):
    for table in (doc.links, doc.shortcuts, doc.charts, doc.number_cards):
        for index, row in enumerate(table, 1):
            row.idx = index
    doc.flags.ignore_permissions = True
    developer_mode = frappe.conf.developer_mode
    try:
        frappe.conf.developer_mode = 0
        doc.save()
    finally:
        frappe.conf.developer_mode = developer_mode
    frappe.clear_cache(doctype="Workspace")
