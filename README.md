# HR Custom

Custom ERPNext/HRMS application containing the Employee HR modifications and
the mobile attendance PWA. The repository contains application metadata and
source code only; employee, attendance, leave, salary, and site data are not
included.

## Production installation

Run from the production bench directory, replacing `your-site` with the site
name:

```bash
bench get-app --branch master https://github.com/Ibrahim-Merhi/hr-custom.git && bench --site your-site install-app hr_custom && bench --site your-site migrate && bench build --app hr_custom
```

ERPNext and HRMS must already be installed on the site. Installation and
migration create the custom DocTypes, fields, reports, Employee form layout,
workspace entries, and PWA assets; they do not copy operational data from the
development site.

## Work schedules and employee hours

- HR creates reusable **Weekly Work Schedule** masters and assigns one schedule to any number of employees.
- The assigned schedule is visible on **Employee**. HR can copy it into employee-specific adjustment rows without changing the shared master.
- **Weekly Employee Hours** compares scheduled hours with matched standard HRMS Employee Checkin IN/OUT logs and flags incomplete logs.
- Employee records contain editable Arabic and English names. Generated transliterations are suggestions; reviewed user corrections can be protected from automatic replacement.

GPS and attendance-audit extensions for Frappe 15.35.0, ERPNext 15.22.2 and
HRMS 15.20.0.

HRMS owns Employee Checkin validation, shift assignment, auto attendance,
Attendance records, late/early calculation, and standard dashboards/reports.
This app only adds branch geofencing, GPS/device/IP audit evidence, exact-time
correction requests, exception alerts, and GPS audit reporting.

It also extends standard HRMS with schedule-based hourly leave. See
[Hourly Leave](docs/hourly_leave.md) for architecture, configuration, behavior,
limitations, and testing.
