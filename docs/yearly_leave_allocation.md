# Yearly Leave Allocation

This master document lets HR prepare one company-wide leave allowance for a year. Submitting it creates and submits the required standard HRMS Leave Allocation documents in a background job. Day and Hour quantities are stored unchanged; `120 Hours` remains `120` in the standard allocation.

## Every new year

1. Create **Yearly Leave Allocation**, select Company and Year, and save.
2. Use **Prepare → Generate Employees**.
3. Use **Copy Previous Year** or **Generate Allowances**.
4. Enter the allowance amounts in the normalized Leave Allowances table.
5. Run **Validate & Preview**, resolve every issue, and submit.
6. Wait for status **Completed**, then verify the summary report and employee balances.

## Initial migration

1. Import Employees and verify `Attendance Device ID` values.
2. Import Leave Types, set `Leave Unit`, and populate `Legacy Leave Type Code`.
3. Normalize the legacy CSV with Year, Legacy Employee Code, Legacy Leave Type Code, From Date, To Date, and Allocated Amount.
4. Call `hr_custom.services.yearly_leave_allocation.import_normalized_csv` with the CSV text, or wrap it in the site's migration command.
5. Review returned exceptions. Unknown codes are never guessed or discarded.
6. Review each generated Draft, validate, then submit explicitly.

Generated Leave Allocations link back to the yearly master and detail row. Retrying is idempotent; unrelated overlapping allocations are reported as conflicts and never overwritten.
