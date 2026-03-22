# Backend Bulk Import Guide

## Purpose

This guide documents the student bulk import contract, especially the preview-first validation flow used by Campus Admin users.

## Current Flow

1. `POST /api/admin/import-students/preview`
2. Review preview errors and approval state
3. Optional: `POST /api/admin/import-preview-errors/{preview_token}/remove-invalid` to keep only valid rows from an invalid preview
4. `POST /api/admin/import-students` with the returned `preview_token`
5. Poll `GET /api/admin/import-status/{job_id}`

## Preview Responsibilities

- validate the uploaded `.xlsx` structure and header order
- validate every row against required fields, duplicate rows inside the file, department names, course names, and email format
- validate that the selected course/program is linked to the selected department in `program_department_association`
- check the target database for conflicts such as:
  - existing user email
  - existing `Student_ID` within the same school
- run database duplicate checks in chunks so preview stays stable for larger uploads
- return `can_commit=true` only when the entire file is approved
- persist the approved rows into a preview manifest under `IMPORT_STORAGE_DIR/previews/`

## Import Responsibilities

- accept only a preview-approved `preview_token`
- queue a background job that reads the stored preview manifest instead of re-reading the workbook
- skip normal row validation during the standard import path because preview is the authoritative validation step
- keep defensive database conflict handling only for late races, such as another process creating the same email after preview approval

## Response Contract

### `POST /api/admin/import-students/preview`

- returns the normal preview counts and row samples
- returns `preview_token` for preview manifests, including invalid previews that need preview-only downloads
- invalid previews can use the same token for preview error exports, but cannot be submitted to the import route

### `POST /api/admin/import-students`

- expects multipart form data with `preview_token`
- returns `400` with `Preview the file first before importing.` when called without a preview token
- returns `400` with `Preview still has invalid rows. Fix them before importing.` when the submitted preview token still has preview errors

### Preview Error Downloads

- `GET /api/admin/import-preview-errors/{preview_token}/download`
  - downloads an Excel file with the failed preview rows plus an `Error` column
- `GET /api/admin/import-preview-errors/{preview_token}/retry-download`
  - downloads an Excel file containing only the preview-failed rows in template format so they can be corrected and re-uploaded
- `POST /api/admin/import-preview-errors/{preview_token}/remove-invalid`
  - removes the preview-failed rows from that preview manifest
  - keeps only the already approved rows
  - returns an updated preview response that can proceed straight to import when at least one valid row remains

## Operational Notes

- retry-failed imports still rebuild a workbook and create a new job, because that flow is explicitly for rows that failed after queueing
- preview manifests live on disk, so `IMPORT_STORAGE_DIR` must be writable by the API and worker processes
- preview approval belongs to the user and school that created it; another user or school cannot consume the same token
- large preview duplicate checks should not use one giant SQL `IN (...)` expression; the repository now chunks those lookups to avoid PostgreSQL stack-depth failures

## How To Test

1. Preview a valid import workbook and confirm `can_commit=true` with a non-empty `preview_token`.
2. Import using that `preview_token` and confirm a pending job is created.
3. Call `POST /api/admin/import-students` without preview and confirm it returns `400`.
4. Preview a workbook that duplicates an existing student email and confirm preview reports `Email already exists`.
5. Preview a workbook that duplicates an existing `Student_ID` inside the same school and confirm preview reports `Duplicate Student_ID within School_ID`.
6. Preview a workbook that uses an existing department and existing course that are not linked together and confirm preview reports `Course is not offered by the selected Department`.
7. From an invalid preview, download the preview error report and retry file and confirm both files contain the failed preview rows.
8. From an invalid preview that still has at least one valid row, call `POST /api/admin/import-preview-errors/{preview_token}/remove-invalid` and confirm the response changes to `can_commit=true` with `invalid_rows=0`.
9. Import using that same cleaned `preview_token` and confirm the job is queued successfully.
