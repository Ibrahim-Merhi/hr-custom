frappe.listview_settings["Leave Application"] = {
    add_fields: [
        "leave_type",
        "employee",
        "employee_name",
        "total_leave_days",
        "from_date",
        "to_date",
        "custom_leave_unit",
        "custom_leave_hours",
        "custom_legacy_balance_deducted",
    ],
    has_indicator_for_draft: 1,
    get_indicator(doc) {
        const status_color = {
            Approved: "green",
            Rejected: "red",
            Open: "orange",
            Draft: "red",
            Cancelled: "red",
            Submitted: "blue",
        };
        const status =
            !doc.docstatus && ["Approved", "Rejected"].includes(doc.status)
                ? "Draft"
                : doc.status;
        return [__(status), status_color[status], "status,=," + doc.status];
    },
    formatters: {
        total_leave_days(value, df, doc) {
            if (doc.custom_leave_unit === "Hours") {
                const hours = flt(doc.custom_leave_hours || doc.custom_legacy_balance_deducted);
                return `${format_number(hours)} ${__("Hours")}`;
            }
            return `${format_number(flt(value))} ${__("Days")}`;
        },
    },
};
