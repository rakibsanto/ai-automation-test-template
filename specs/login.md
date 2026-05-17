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

### Disabled Scenarios

#### Scenario 1
Email empty + Password empty  
Expected: **Disabled**

#### Scenario 2
Email entered + Password empty  
Expected: **Disabled**

#### Scenario 3
Email empty + Password entered  
Expected: **Disabled**

#### Scenario 4
Email entered + Password less than 6 characters  
Expected: **Disabled**

---

### Enabled Scenario

#### Scenario 5
Valid email entered + Password 6+ characters  
Expected: **Enabled**

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

## Unauthorized Access
Direct URL access blocked without login

Example:
Attempt:
`/dashboard`

Expected:
Redirect to Login page

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

## Large Desktop
Resolution:
2560x1440

Expected:
- Centered login container
- Proper whitespace usage
- No stretched UI elements
- Consistent component sizing

---

## Standard Desktop
Resolution:
1920x1080

Expected:
- Proper alignment and spacing
- Full visibility
- Balanced layout

---

## Small Desktop
Resolution:
1600x900

Expected:
- No overflow
- All content visible
- Proper button spacing

---

## Laptop
Resolution:
1366x768

Expected:
- Fully visible without overflow
- Login form centered
- No clipping

---

## Small Laptop
Resolution:
1280x720

Expected:
- Form fits viewport
- No vertical cutoff
- Buttons accessible

---

## Tablet Landscape
Resolution:
1024x768

Expected:
- Responsive horizontal layout
- Proper spacing maintained

---

## Tablet Portrait
Resolution:
768x1024

Expected:
- Responsive stacked layout
- Inputs full-width

---

## Large Mobile
Device:
iPhone 14 Pro Max

Resolution:
430x932

Expected:
- Proper alignment
- Comfortable spacing
- Touch-friendly controls

---

## Standard Mobile
Device:
iPhone 12 / 13

Resolution:
390x844

Expected:
- Inputs aligned
- Buttons clickable
- No horizontal scrolling

---

## Small Mobile
Device:
iPhone SE

Resolution:
375x667

Expected:
- No content cutoff
- Full button visibility
- Scroll only if required

---

## Android Medium
Device:
Samsung Galaxy S21

Resolution:
360x800

Expected:
- Responsive layout
- Proper touch target spacing

---

## Android Small
Device:
Small Android Device

Resolution:
320x568

Expected:
- Layout remains usable
- Text readable
- No overlapping elements

---

## Foldable Device
Device:
Galaxy Fold

Resolution:
280x653 (folded)

Expected:
- Adaptive layout
- Inputs remain accessible

---

## Ultra Wide Screen
Resolution:
3440x1440

Expected:
- Centered login form
- No excessive stretching

---

## Zoom Testing

### Browser Zoom 80%
Expected:
No layout break

---

### Browser Zoom 100%
Expected:
Default proper rendering

---

### Browser Zoom 125%
Expected:
No overflow

---

### Browser Zoom 150%
Expected:
Still usable

---

## Orientation Testing

### Portrait Mode
Expected:
Optimized vertical stacking

---

### Landscape Mode
Expected:
Proper horizontal fit

---

## Responsive Validation Rules

The login page must ensure:

- No horizontal scrolling
- No overlapping text
- No hidden buttons
- Proper field spacing
- Tap targets minimum accessible size
- Logo scales correctly
- Error messages remain readable
- Submit button visible on all screen sizes

---

## Orientation Support

### Portrait
Supported

### Landscape
Supported

---

# 6. UI / UX Requirements

## Logo Display
Raad logo visible at top

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