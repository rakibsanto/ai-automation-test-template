# Platform Fee Management

## Overview

The Platform Fee is managed by the Super Admin from the Account Settings.

This fee is applied to all tutor earnings when a student books and completes a session.

### How it works:
- Platform Fee is deducted from tutor earnings per session.
- Remaining amount is added to tutor earnings.
- Platform Fee is collected by the Admin.

---

# Open Platform Fee Settings

1. Login as Super Admin.
2. Open the **Sidebar**.
3. Go to **Account Settings**.
4. Click on **Platform Fee** card.

---

# Update Platform Fee

1. A modal will open after clicking the Platform Fee card.
2. Inside the modal, there will be a field:
   - **New Platform Fee**

---

## Update Process

1. Enter the desired platform fee amount.
2. Click on **Save Changes** button.
3. A success message should appear:
   - "Platform Fee Updated Successfully"

---

## Expected Result

- The updated platform fee will be applied globally.
- It will affect all tutors automatically.

---

# Platform Fee Calculation Logic

When a student books a session:

1. Total session earning is calculated.
2. Platform Fee is deducted from tutor earning.
3. Remaining amount is added to tutor wallet/earning.
4. Platform Fee amount is assigned to Admin.

---

# Verification & Testing

## Student Enrollment Flow

1. Student enrolls in a tutor session/course.
2. System calculates platform fee deduction.
3. Student completes payment.

### Expected Check:
- Platform fee is correctly deducted
- Tutor earning is updated correctly
- Admin receives platform fee amount

---

## Admin Verification

1. Go to Admin Panel.
2. Open **Instructor / Tutor Profile View**.
3. Check tutor earnings breakdown.
4. Verify:
   - Platform fee deduction is correct
   - Final earning is accurate

---

## Tutor Profile Check

1. Tutor logs into profile.
2. Navigate to earnings section.
3. Verify:
   - Session earnings
   - Deducted platform fee
   - Final payable amount

---

# Functional Checks

- Platform fee update works correctly
- Value updates globally for all tutors
- Earnings calculation is accurate
- Admin receives correct fee
- Tutor sees correct deduction
- No mismatch in session-wise calculation