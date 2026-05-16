# Reset Password (Super Admin)

## Overview

The Reset Password feature allows the Super Admin to manually change their account password from the Account Settings panel.

This feature is used for:
- Security updates
- Password recovery (manual change)
- Credential rotation

After resetting, the new password must be used for future logins.

---

# Open Reset Password

1. Login as Super Admin.
2. Open the **Sidebar**.
3. Go to **Account Settings**.
4. Click on **Reset Password** card.

---

# Reset Password Modal

After clicking the card, a modal will open containing password fields.

---

## Fields

### New Password
- Enter a new strong password.
- Must be:
  - Unique
  - Strong (secure format required)

### Show/Hide Password
- Eye (👁) icon available to toggle password visibility.

---

### Confirm Password
- Re-enter the same password for confirmation.
- Must exactly match the New Password field.

---

# Reset Password Process

1. Enter a strong new password.
2. Confirm the same password in the confirmation field.
3. Click on **Reset Password** button.
4. System validates both fields.

---

## Success Scenario

- If valid:
  - Password is updated successfully.
  - Success message is shown.

---

## Failure Scenario

- If passwords do not match:
  - Error message is shown.
- If password is weak:
  - Validation error is shown.

---

# Post Reset Behavior

After successful reset:

1. Old password becomes invalid.
2. New password becomes active immediately.
3. Super Admin must use the new password for login.
4. Next login requires updated credentials.

---

# Functional & Validation Checks

## Password Rules
- Must be strong
- Must be unique
- Must meet system security requirements

## Confirmation Check
- New Password and Confirm Password must match

## UI Checks
- Eye icon works properly
- Modal opens and closes correctly

## Security Checks
- Old password should no longer work
- New password should be immediately active

## Login Verification
- Login works only with updated password
- Invalid old password is rejected