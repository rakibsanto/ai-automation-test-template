# ProWhats Login Page Specification

## Module
Authentication / Login

---

# 1. Functional Requirements

## Login Fields

### Email Field
- Required
- Accept valid email format
- Trim leading/trailing spaces
- Case insensitive

Placeholder:
`Enter your email`

Max Length:
100 characters

---

### Password Field
- Required
- Minimum 6 characters
- Maximum 50 characters
- Masked by default

Placeholder:
`Enter your password`

---

### Show / Hide Password
- Toggle password visibility
- Default: Hidden

---

### Login Button
States:
- Enabled when both fields are filled
- Disabled when empty

---

### Forgot Password
Clickable navigation to password recovery page

---

# 2. Role-Based Authentication

## Admin Credential
Email: ammarahmedmk@gmail.com  
Password: @mm@rpr0

Redirect:
**Admin Panel**

---

## Agent Credential
Email: rakibsanto.1998@gmail.com  
Password: 111111

Redirect:
**Company Section**

---

## Owner Credential
Redirect:
**Company Section**

---

# 3. Validation Rules

## Email Validation

Accept:
- Standard email format

Reject:
- Missing @
- Missing domain
- Special invalid characters
- Empty value

Error:
`Enter a valid email address`

---

## Password Validation

Reject:
- Less than 6 characters
- Empty field
- Only spaces

Error:
`Password must be at least 6 characters`

---

# 4. Security Requirements

## Authentication Security
- Password encrypted in transit
- Backend credential verification
- Secure session token generation

---

## Failed Login Protection
After 5 failed attempts:

- Temporarily block login for 15 minutes

Error:
`Too many failed login attempts. Try again later.`

---

## Session Security
- Auto logout after 30 minutes inactivity
- Session invalidation after logout
- Prevent session reuse

---

## Unauthorized Access
Direct URL access blocked without login

Example:
Attempt:
`/admin/dashboard`

Expected:
Redirect to Login page

---

## Brute Force Protection
- Rate limiting enabled
- IP monitoring

---

## XSS Protection
Reject script injection in email/password field

Example:
`<script>alert(1)</script>`

---

## SQL Injection Protection
Reject malicious inputs

Example:
`' OR 1=1 --`

---

# 5. Responsive Requirements

## Desktop
Resolution:
1920x1080

Expected:
Proper alignment and spacing

---

## Laptop
1366x768

Expected:
Fully visible without overflow

---

## Tablet
768x1024

Expected:
Responsive layout

---

## Mobile
375x667

Expected:
- Inputs properly aligned
- Buttons clickable
- No horizontal scrolling

---

## Orientation Support

### Portrait
Supported

### Landscape
Supported

---

# 6. UI / UX Requirements

## Logo Display
ProWhats logo visible at top

---

## Input Focus State
Highlighted border on focus

---

## Error Styling
- Red border
- Visible error message

---

## Loading State
After login click:

- Show loader
- Disable button
- Prevent multiple submissions

---

# 7. Performance Requirements

## Page Load Time
Maximum:
3 seconds

---

## Login Response Time
Maximum:
2 seconds

---

# 8. Browser Compatibility

Supported Browsers:

- Chrome
- Firefox
- Edge
- Safari

Latest 2 versions

---

# 9. Accessibility Requirements

- Keyboard navigable
- Tab order correct
- Enter key submits form
- Screen-reader compatible labels
- Adequate color contrast

---

# 10. Error Handling

## Invalid Credentials
`Invalid email or password`

---

## Empty Fields
`All fields are required`

---

## Server Error
`Something went wrong. Please try again later.`

---

# 11. Logging & Audit

System should log:

- Successful login
- Failed login
- Logout
- Role accessed
- Timestamp
- Device/browser info

---

# 12. Test Scenarios

## Positive Tests
- Valid admin login
- Valid agent login
- Valid owner login

---

## Negative Tests
- Invalid email
- Wrong password
- Empty fields
- Locked account
- Expired session

---

## Security Tests
- SQL injection
- XSS
- Brute force
- Session hijacking

---

## Responsive Tests
- Mobile
- Tablet
- Desktop

---

## Cross Browser Tests
All supported browsers