# Endpoint Audit: Frontend vs Backend Contract

## Auth & User
| Endpoint | Method | Frontend Expects | Backend Status | Action |
|---|---|---|---|---|
| `/token` | POST | `{ username, password }` → `{ access_token, token_type, ...}` | ✓ Working | None |
| `/auth/change-password` | POST | `{ current_password, new_password }` | ✓ Working | None |
| `/auth/forgot-password` | POST | `{ email }` → generic message | ✓ Working (lastname reset) | None |
| `/users/me` | GET | Current user profile | Verify shape | Check |
| `/users/{userId}` | GET | User details | Verify shape | Check |
| `/users/{userId}` | PATCH | User update payload | ✓ Likely working | Verify |
| `/users/{userId}/reset-password` | POST | `{ password }` | ✓ Working | None |

## Students
| Endpoint | Method | Frontend Expects | Backend Status | Action |
|---|---|---|---|---|
| `/users/students/` | POST | Manual create student | ✓ Lastname validation | None |
| `/users/admin/students/` | POST | Create student profile | Verify working | Check |
| `/api/users/student-profiles/{profileId}` | PATCH | Update student profile | Verify working | Check |
| `/api/admin/import-students` | POST | File upload → preview token | Verify shape | Check |
| `/api/admin/import-students/preview` | POST | Preview data (JSON) → start import | Verify working | Check |
| `/api/admin/import-status/{jobId}` | GET | Import job status | Verify shape | Check |
| `/api/admin/import-students/retry-failed/{jobId}` | POST | Retry failed rows | Verify working | Check |
| `/api/admin/import-preview-errors/{previewToken}/remove-invalid` | PATCH | Remove bad rows | Verify working | Check |

## Events
| Endpoint | Method | Frontend Expects | Backend Status | Action |
|---|---|---|---|---|
| `/events/` | GET | List events (paginated) | Verify pagination | Check |
| `/events/` | POST | Create event | Verify geofence fields | Check |
| `/events/{eventId}` | GET | Event detail | Verify shape | Check |
| `/events/{eventId}` | PATCH | Update event | Verify geofence fields | Check |
| `/events/{eventId}` | DELETE | Delete event | ✓ Likely working | None |
| `/api/governance/events` | GET | Governance events (paginated) | Verify pagination | Check |
| `/api/governance/events` | POST | Create governance event | Verify working | Check |

## Attendance
| Endpoint | Method | Frontend Expects | Backend Status | Action |
|---|---|---|---|---|
| `/face/face-scan-with-recognition` | POST | `{ eventId, embedding, geolocation, timestamp }` | Verify shape & error codes | Check |
| `/attendance/face-scan-timeout` | POST | Timeout marker | Verify working | Check |
| `/api/users/me/attendance` | GET | Student's own attendance (paginated) | Verify pagination | Check |
| `/api/attendance/event/{eventId}` | GET | Event attendance list (paginated) | Verify pagination | Check |
| `/api/students/{studentId}/attendance-report` | GET | Student report | Verify shape | Check |
| `/api/events/{eventId}/attendance-report` | GET | Event report | Verify shape | Check |
| `/attendance/summary` | GET | Summary dashboard | Return zeros not errors | Check |

## Pagination (all list endpoints)
| Endpoint | Params | Expected Response | Action |
|---|---|---|---|
| All `/GET` list endpoints | `page`, `page_size`, `search`, filters | `{ items: [...], total, page, page_size, total_pages }` | Standardize across backend |

## Geofence & Location
| Endpoint | Method | Frontend Expects | Backend Status | Action |
|---|---|---|---|---|
| `/face/face-scan-with-recognition` | POST | Payload includes `{ lat, lng, accuracy }` | Check coordinates handling | Check |
| Distance validation | — | Haversine formula, `<=` boundary | Verify math, error code | Check |
| Error messages | — | `OUTSIDE_GEOFENCE` code + distance string | Map error codes | Step 6 |

## Face Recognition Error Codes
| Error | User Message | Code | Action |
|---|---|---|---|
| No face | "No face detected. Move closer and face the camera directly." | `NO_FACE` | Map/document |
| Multiple faces | "Multiple faces detected. Only one person at a time." | `MULTIPLE_FACES` | Map/document |
| Face too small | "Move closer to the camera." | `FACE_TOO_SMALL` | Map/document |
| Face too close | "Move slightly back from the camera." | `FACE_TOO_CLOSE` | Map/document |
| Poor lighting | "Lighting is too low. Move to a brighter area." | `POOR_LIGHTING` | Map/document |
| Liveness failed | "Liveness check failed. Please use a real face, not a photo or screen." | `LIVENESS_FAILED` | Map/document |
| Not recognized | "Face not recognized. Please try again or contact your instructor." | `FACE_NOT_RECOGNIZED` | Map/document |
| Not enrolled | "You are not enrolled in this event." | `NOT_ENROLLED` | Map/document |
| Already marked | "Attendance already recorded at HH:MM." | `ALREADY_MARKED` | Map/document |
| Outside geofence | "You are X meters from the event location (allowed: Y meters)." | `OUTSIDE_GEOFENCE` | Map/document |
| Outside time window | "Attendance is closed for this event." | `OUTSIDE_TIME_WINDOW` | Map/document |
| Service error | "Service temporarily unavailable. Please try again." | `SERVICE_ERROR` | Map/document |

## Next Steps
1. Verify list endpoint pagination contract (items, total, page, page_size, total_pages)
2. Check face error code response shape
3. Confirm geofence distance calculation uses Haversine
4. Standardize pagination across all list endpoints
5. Map error codes to user-facing messages per table above
