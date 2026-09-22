# Hourly Leave

## Overview

HR Custom extends the installed HRMS leave documents; it does not replace them.
Day-based Leave Types continue through the original HRMS code. Leave Types whose
`Leave Unit` is `Hours` use the employee's weekly schedule to calculate and deduct
hours without converting them to fractional days.

## Architecture

- Standard `Employee`, `Employment Type`, `Leave Type`, `Leave Allocation`,
  `Leave Application`, `Holiday List`, and `Leave Ledger Entry` remain authoritative.
- Two child tables store default and employee-specific weekly schedules.
- `hr_custom.services.work_schedule` resolves expected hours and holidays.
- `hr_custom.services.hourly_leave` calculates breakdowns and balances.
- Narrow `Leave Application` and `Leave Allocation` subclasses branch only when
  `Leave Type.custom_leave_unit == "Hours"`.
- Server validation always rebuilds calculated fields. Browser values are previews only.

## HR setup

1. Open an Employment Type and choose `Days`, `Hours`, or `Both` in
   **Leave Calculation Mode**.
2. For `Hours` or `Both`, add one enabled row for every relevant weekday under
   **Weekly Working Hours**. Use the **Complete Weekly Schedule** button to add
   missing weekdays with zero hours.
3. Assign that Employment Type to the Employee.
4. If the employee differs from the default schedule, enable
   **Use Custom Work Schedule** on Employee and configure its weekly table.
5. Open Leave Type and set **Leave Unit** to `Hours`. Existing Leave Types default
   safely to `Days`.
6. Create and submit a standard Leave Allocation. Its quantity represents hours
   for an hourly Leave Type (for example, `80`).
7. Create a standard Leave Application. Choose full scheduled hours, or choose
   partial hours for a single date and enter the requested quantity.

## Calculation rules

- Full leave sums scheduled hours for each date in the inclusive range.
- Holidays use the standard employee Holiday List and deduct zero hours.
- Weekdays configured with zero hours deduct zero hours.
- A range containing no deductible scheduled hours is rejected.
- Partial leave is restricted to one date and must be greater than zero and no
  greater than that date's scheduled hours.
- Employee schedules take precedence only when the override checkbox is enabled
  and the employee table contains enabled rows; otherwise Employment Type is used.
- A missing schedule is an error for hourly leave.

## Balances and lifecycle

Standard Leave Allocation stores hour quantities. Submitted, Approved hourly Leave
Applications consume `custom_leave_hours`. A standard Leave Ledger Entry is also
created with the negative hour quantity for audit and compatibility. Cancellation
deletes that transaction's ledger entry and removes the application from used-hour
queries, restoring the balance naturally. Negative balances follow the standard
Leave Type `Allow Negative Balance` setting.

The application displays scheduled hours, requested leave hours, available balance,
balance after leave, and a per-date breakdown. Day leave keeps standard HRMS fields,
calculations, attendance behavior, workflow, submission, cancellation, and amendment.

HR users can open the **Hourly Leave Balance** report and filter by Company,
Employee, Leave Type, and As Of Date. It shows allocated, used, and remaining hours.

## Permissions

The preview API is authenticated. Employees may preview only their own data; HR User,
HR Manager, and System Manager may preview other employees. Save and submit continue
to use standard Leave Application permissions and workflow.

## Attendance and payroll compatibility

Hourly Leave Applications do not create full-day `Attendance: On Leave` records,
because that would misrepresent partial leave. The hourly quantity and date breakdown
are report-friendly and can support a later explicit partial-attendance/payroll policy.
Day leave retains standard attendance and payroll behavior.

## Migration compatibility

Legacy audit fields are available on Leave Application, but production CSV import is
intentionally not implemented. Existing records and Leave Types remain day-based.
Future migration should populate the custom hourly fields only for records confirmed
to represent hours; an absent employee joining date should be mapped to `1900-01-01`
in the later import process.

## Known limitations

- Partial hours are single-day only.
- Weekly schedules do not yet have effective-date history; schedule access is isolated
  in one service so date-aware schedule records can be introduced later.
- Hourly leave does not yet generate a partial Attendance record or directly prorate
  payroll. No fixed hours-per-day conversion is made.
- The standard HRMS mobile leave UI is not customized; Desk Leave Application contains
  the complete hourly preview and breakdown.

## Testing and troubleshooting

Run:

```bash
bench --site <site> migrate
bench --site <site> run-tests --app hr_custom --module hr_custom.tests.test_hourly_leave
bench --site <site> run-tests --app hr_custom
```

If calculation reports a missing schedule, confirm enabled child rows exist either on
the Employee override or on the Employee's Employment Type. If a date deducts zero,
check both the weekday hours and the employee's resolved Holiday List.
