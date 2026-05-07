# Login Flow Test Cases (Frontend)

## Base Steps (Given by User)

1. Go to the website: [https://dev.mehadedu.com/en](https://dev.mehadedu.com/en)
2. Click Login button from header section
3. Login modal should open
4. Select +880 country code from dropdown
5. Input number: 98976564
6. Number max length: 12 digits
7. 10 digits valid for BD
8. Click "Send Code" button
9. Receive 6-digit verification code (e.g., 123456)
10. Verification code max length: 6
11. Show login success message
12. Authentication complete

---

## Additional Test Scenarios (Recommended)

### 🔹 UI / UX Validation

* Login button visible in header
* Login modal design aligned properly
* Modal should close on clicking outside / close icon
* Placeholder text visible in input fields
* Country code dropdown searchable

### 🔹 Input Field Validation (Phone Number)

* Empty input → show "Required" error
* Less than 10 digits → show validation error
* More than 12 digits → restrict input / error message
* Accept only numeric values (no letters/symbols)
* Trim spaces automatically

### 🔹 Country Code Validation

* Default country code should be +880 (if BD-based app)
* User can change country code
* Number validation updates based on country code

### 🔹 Send Code Button Validation

* Disabled when input is empty
* Enabled only when valid number is entered
* Show loader after clicking button
* Prevent multiple clicks (debounce / disable)

### 🔹 OTP / Verification Code Validation

* OTP field required
* Max length = 6 digits
* Accept only numeric values
* Show error for incorrect OTP
* Show error for expired OTP
* Auto-focus next input (if split boxes)

### 🔹 OTP Flow Behavior

* OTP auto-fill (if supported)
* Resend OTP button available
* Resend timer (e.g., 30s)
* Limit OTP resend attempts

### 🔹 Error Handling

* Invalid number → show error message
* Network error → show retry option
* Server error → proper message display

### 🔹 Success Flow

* Show success message (toast / alert)
* Redirect to dashboard/home page
* Store auth token/session properly

### 🔹 Security Validation

* OTP should expire after defined time
* Prevent brute force (multiple wrong attempts)
* Mask phone number (e.g., 019******07)

### 🔹 Performance

* OTP send response time < 3 seconds
* Login flow smooth without UI lag

### 🔹 Cross Browser Testing

* Chrome, Firefox, Edge support
* Mobile responsiveness (Android/iOS)

### 🔹 Accessibility

* Keyboard navigation support
* Screen reader compatibility
* Proper label and aria attributes

---

## Bonus (Automation Scope)

* Automate login using Playwright / Cypress
* Validate API response for OTP send & verify
* Check token generation after login

---

## Notes

* Test with real and dummy numbers
* Test WhatsApp OTP delivery delay scenarios
* Verify backend + frontend consistency

---
