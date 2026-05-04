# Page Name: [Your Page Name Here]

## Overview
<!-- Replace this with a short description of the page -->
This page allows users to [describe the main purpose].

## URL
<!-- The path for this page — relative or absolute -->
/your-page-path

## UI Elements
<!-- List every interactive element: labels must match what's visible on screen -->
| Element         | Selector / Hint                     | Notes                    |
|-----------------|-------------------------------------|--------------------------|
| Email field     | input[type='email']                 | Required                 |
| Password field  | input[type='password']              | Required, masked         |
| Submit button   | button[type='submit']               | Text: "Login"            |
| Error message   | [data-testid='error'], .error-msg   | Shown on failure         |
| Success banner  | .success, [role='alert']            | Shown on success         |

<!--
TIPS:
- Use CSS selectors: input[type='email'], #email, .form-field
- Use data-testid: [data-testid='submit-btn']
- Use role: [role='button'][name='Login']
- Use placeholder: input[placeholder='Enter your email']
- Common names that trigger automatic selector inference:
    email, username, password, confirm_password, submit, login,
    first_name, last_name, phone, otp, search, error, success
-->

## Requirements
<!-- What must be true for this page to work correctly -->
- REQ-001: User can [describe action]
- REQ-002: Invalid input shows an error message
- REQ-003: Valid input navigates to [next page]
- REQ-004: Page loads within 3 seconds
- REQ-005: Page is accessible (no WCAG violations)

## User Flows
<!-- Step-by-step user journeys — one flow per heading -->

### Flow 1: Happy Path (Success)
1. Navigate to page
2. Fill in [field] with valid data
3. Click [button]
4. Expect [result — URL, message, element visible]

### Flow 2: Error Path (Failure)
1. Navigate to page
2. Fill in [field] with invalid data
3. Click [button]
4. Expect error message to appear

### Flow 3: Edge Case Path
1. Navigate to page
2. Leave [field] empty
3. Click [button]
4. Expect validation message

## Validation Rules
<!-- What inputs are accepted/rejected and what errors appear -->
| Field    | Rule                     | Error Message                        |
|----------|--------------------------|--------------------------------------|
| Email    | Must be valid email      | "Please enter a valid email address" |
| Password | Minimum 8 characters     | "Password must be at least 8 chars"  |
| Password | Must contain uppercase   | "Include at least one uppercase letter" |
| Email    | Required — cannot be empty | "Email is required"                |

## Edge Cases
<!-- Unusual inputs that must be handled gracefully -->
| ID    | Scenario                                | Expected Behavior                     |
|-------|-----------------------------------------|---------------------------------------|
| EC-001 | Submit empty form                      | Show required field errors            |
| EC-002 | Email with spaces: "user @test.com"    | Show invalid email error              |
| EC-003 | Very long email (200+ chars)           | Show length validation error or trim  |
| EC-004 | Password with only spaces              | Show invalid password error           |
| EC-005 | SQL injection: ' OR 1=1 --             | Show error, do NOT execute SQL        |
| EC-006 | XSS: <script>alert(1)</script>         | Render as text, do NOT execute        |
| EC-007 | Unicode password: 密码1234              | Accept or show clear error            |
| EC-008 | Double-click submit button             | Submit only once, not duplicate       |
| EC-009 | Paste email with leading/trailing space | Trim and accept                      |

## API Contract
<!-- HTTP requests the page makes — helps test_generator write API tests -->
| Method | Endpoint              | Request Body               | Success Response         | Error Response        |
|--------|-----------------------|----------------------------|--------------------------|-----------------------|
| POST   | /api/auth/login       | { email, password }        | 200 { token, user }      | 401 { error: "..." } |
| POST   | /api/auth/logout      | {}                         | 200 {}                   | —                     |

<!--
TIP: If you don't know the exact endpoints, write what you expect.
The agent will use these as hints for API/network tests.
-->

## Test Data
<!-- Concrete values to use in tests — replace with your own -->
| Category         | Value                                | Notes                       |
|------------------|--------------------------------------|-----------------------------|
| Valid email      | testuser@mailinator.com              | Use mailinator for disposable |
| Valid password   | Test@1234!                           | From TEST_PASSWORD env var  |
| Invalid email    | notanemail                           | Missing @ symbol            |
| Invalid email 2  | @domain.com                          | Missing username             |
| Short password   | abc                                  | Under minimum length         |
| Long email       | a@b.com (repeat 50x)                 | Boundary test                |
| Empty email      | (empty string)                       | Required field test          |
| XSS payload      | <script>alert('xss')</script>        | Security test                |
| SQL injection    | ' OR '1'='1                          | Security test                |
| Unicode          | tëst@éxample.com                     | i18n test                   |
| Arabic           | مستخدم@test.com                      | RTL i18n test                |

<!--
═══════════════════════════════════════════════════════════════════
HOW TO ADAPT THIS FILE FOR YOUR PROJECT
═══════════════════════════════════════════════════════════════════

1. Copy this file: cp specs/TEMPLATE.md specs/your-page.md
2. Edit the sections:
   - Change "Page Name" to your page (e.g., "Signup", "Dashboard", "Checkout")
   - Set the correct URL path
   - Update UI Elements with your actual selectors
   - List your real requirements (what the page must do)
   - Describe actual user flows (steps + expected result)
   - List validation rules (what inputs pass/fail and what error shows)
   - Add edge cases specific to your page
   - Set the API endpoint(s) the page calls
   - Use real test data from your staging environment

3. Run the agent:
   python ai_engine/agent.py

That's it. The agent will:
✅ Parse your spec deterministically (no AI guessing structure)
✅ Extract selectors, flows, validations, edge cases
✅ Generate 22 types of tests with your actual data
✅ Validate all generated code before running
✅ Run tests against your URL
✅ Self-heal failures with AI
✅ Write bug tickets for all failures
✅ Generate HTML report with screenshots

EXAMPLE SPECS IN THIS REPO:
  specs/login.md           — Login page
  specs/reset-password.md  — Password reset flow
  specs/signup.md          — Signup/registration

═══════════════════════════════════════════════════════════════════
-->
