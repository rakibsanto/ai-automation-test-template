# Promo Code Management

## Overview

The Promo Code section is managed by the Super Admin.

Promo codes are used to provide discounts to students during:
- Package purchase
- Course enrollment
- Session booking (if applicable)

These promo codes are applied at checkout and directly affect the final payable amount.

---

# Open Promo Code Dashboard

1. Login as Super Admin.
2. Open the **Sidebar**.
3. Go to **Account Settings**.
4. Click on **Promo Codes**.
5. The Promo Code Dashboard will open.

---

# Search Promo Code

1. Use the search input field.
2. Enter:
   - Promo Code Name
   - Promo Code ID
3. Matching results will be displayed.

---

# Promo Code Status

## Active
- If status is **Active**, the promo code can be used by students.

## Disable
- If status is **Disable**, the promo code cannot be used.

---

# Promo Code Types

## Percentage Discount
- Applies discount based on percentage (e.g., 10%, 20%)

## Fixed Discount
- Applies fixed amount discount (e.g., $5, $10)

---

# Create Promo Code

1. Click on **Create Promo Code** button.
2. A modal will open.

---

## Fields

### Promo Code Name
- Enter unique promo code.

### Discount Type
- Select:
  - Percentage
  - Fixed Amount

### Discount Value
- Enter discount value based on selected type.

### Usage Limit
- Define how many times the promo code can be used.

### Expiry Date
- Set expiration date for the promo code.

### Status Toggle
- Active / Disable

---

# Create Process

1. Fill all required fields.
2. Click on **Create**.
3. Promo code will be created successfully.
4. It becomes available for student usage based on status.

---

# Edit Promo Code

1. Click on **Action Button**.
2. Select **Edit**.
3. Update:
   - Discount value
   - Expiry date
   - Usage limit
   - Status
4. Click **Save**.

---

# Delete Promo Code

1. Click on **Action Button**.
2. Select **Delete**.
3. Confirm deletion.

---

# Student Side Usage Check

1. Go to checkout (package/course/session booking).
2. Enter promo code.
3. Apply code.

## Expected Behavior
- Valid promo code applies discount correctly
- Invalid promo code shows error
- Expired promo code does not work
- Disabled promo code cannot be used

---

# Functional & Validation Checks

## Search
- Search works by name and ID

## Status
- Active codes are usable
- Disabled codes are not usable

## Discount Logic
- Percentage discount calculates correctly
- Fixed discount deducts properly

## Usage Limit
- Code stops working after limit is reached

## Expiry
- Expired codes are blocked

## Student Flow
- Promo code applies correctly in checkout
- Discount reflects in final price