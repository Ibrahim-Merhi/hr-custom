# Hourly Leave Deployment Checklist

## Before deployment

- Take database and site-file backups.
- Confirm the target versions match the tested Frappe 15.35.0, ERPNext 15.22.2,
  and HRMS 15.20.0 versions, or rerun regression tests against the target versions.
- Confirm no production legacy CSV import is included.
- Review the local diff and create the final commit only after acceptance testing.

## Deploy

```bash
cd /home/frappe/frappe-bench
bench --site <live-site> backup --with-files
bench --site <live-site> migrate
bench build --app hr_custom
bench --site <live-site> clear-cache
bench restart
```

## Verify

- Existing Leave Types show `Days` and existing day leave still saves/submits.
- Create the documented Hourly Teacher schedule and 80-hour allocation.
- Verify Tuesday–Wednesday deducts 10 hours and Friday partial leave deducts 2.
- Verify both cancellations restore the balance to 80.
- Confirm the Hourly Leave Balance report matches the applications.
- Confirm Employee-role preview cannot access another employee.
- Confirm payroll is not prorated automatically and hourly applications do not create
  misleading full-day Attendance records.

## Rollback

Restore the pre-deployment database and files backup if migration or acceptance fails.
Do not remove custom fields manually from a live database because legacy audit values
may later rely on them.
