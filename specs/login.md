# Page: Mehad — Homepage & Login Modal
**URL:** `https://dev.mehadedu.com/en`
**Type:** Marketing Homepage + Authentication Entry Point
**Priority:** P0 — Critical path; login blocks all booking and tutor-interaction workflows
**Platform:** Mehad (Mahad Al-Maarefa Company) — Saudi Arabia's #1 Online Tutoring Platform
**Locale:** English (`/en`) | Arabic (`/ar`) — bilingual, RTL/LTR toggle

---

## Page Purpose

Landing page for Mehad, an online tutoring marketplace connecting students with certified Saudi
tutors. The page markets the platform, showcases top tutors, enables tutor discovery via a search
form, and provides the primary entry point for authentication via a WhatsApp OTP login modal.

---

## UI Elements — Header / Navigation

| Element | Identifier Hint | Type | Visible |
|---|---|---|---|
| Mehad logo | `aria-label="Mehad homepage"`, `href="/en"` | Image link | Always |
| Hamburger menu | `aria-label="Open menu"`, `md:hidden` | Sheet trigger (mobile only) | Mobile only |
| Home nav link | `href="/en"` | Anchor | Desktop |
| Find Tutors dropdown | `aria-haspopup="menu"`, `data-slot="dropdown-menu-trigger"` | Dropdown button | Desktop |
| Become a Tutor link | `href="/en/become-tutor"` | Anchor | Desktop |
| How It Works link | `href="/en/how-mehad-works"` | Anchor | Desktop |
| About Us link | `href="/en/about-us"` | Anchor | Desktop |
| Language: AR button | `aria-label="العربية"` | Toggle button | Always |
| Language: EN button | `aria-label="English"`, active/selected state | Toggle button (active) | Always |
| Log In button (desktop) | `hidden md:inline-flex`, `aria-label="Login"` | Button → opens modal | Desktop |
| Log In button (mobile) | `md:hidden`, `aria-label="Login"` | Button → opens modal | Mobile only |
| User avatar / name | Shown after login (e.g., "Automations Student") | Profile display | Post-login |

---

## UI Elements — Hero Section

| Element | Content | Type |
|---|---|---|
| Badge | "Saudi Arabia's #1 Education Platform" | Label |
| Headline H1 | "Learn with the Best Teachers in Saudi Arabia" | Heading |
| Sub-headline | "One-on-one online lessons for all subjects • Flexible scheduling • Certified teachers" | Paragraph |
| Stat: Teachers | "+1,200 Certified Teachers" | Counter |
| Stat: Students | "+50,000 Students Helped" | Counter |
| Stat: Satisfaction | "98% Student Satisfaction" | Counter |

---

## UI Elements — Tutor Search Form

| Element | Identifier Hint | Type | Required |
|---|---|---|---|
| Section label | "Find Your Perfect Teacher / Over 1,200 teachers available now" | Label | — |
| Subject dropdown | "Select subject" placeholder | Select / combobox | No |
| Level dropdown | "Select Level" placeholder | Select / combobox | No |
| Available Time dropdown | "Select availability" placeholder | Select / combobox | No |
| Price Range dropdown | "Select Price Range" placeholder | Select / combobox | No |
| Find a Teacher button | `text="Find a Teacher"` | Submit → `/en/find-tutors` | — |

---

## UI Elements — Homepage Sections

| Section | Content |
|---|---|
| **STUDY SUBJECTS** | "Most Requested Subjects" — Physics (9), Math (25), Algebra (12), Chemistry (11), Physical Chemistry (2) |
| **HOW IT WORKS** | "Three Steps to Success" — Choose a Teacher, Book a Session, Start Learning |
| **OUR FEATURES** | Certified Teachers, Instant Booking, Live Lessons, Secure Payments, Rating System |
| **Teachers** | "Our Top Teachers" — horizontal scroll cards; each has avatar, certified badge, name, subject, experience, student count, rating, hourly price |
| **STUDENT REVIEWS** | "What Our Students Say / Over 6+ students trust Mehad" — carousel with avatar, name, role, quote |
| **CTA** | "Start Learning Today with Mehad" — "Find your tutor" + "Become a tutor" CTAs |

---

## UI Elements — Footer

| Section | Links |
|---|---|
| Brand | Mehad logo + company description |
| EXPLORE | Home, Find Tutors, Subjects, How it Works, Pricing |
| COMPANY | About us, Contact us, Faqs, Blog, Careers |
| POLICIES | Privacy Policy, Terms & Use, Refund Policy, Cookie Policy |
| Copyright | "All rights reserved \| 2026 Mahad Al-Maarefa Company" |
| Tag | "Made with ❤ in Saudi Arabia" |

---

## Login Modal — Detailed Spec

**Trigger:** Click "Log In" button (desktop or mobile)
**Component type:** `role="dialog"` — full-height right-side sheet (drawer) on mobile, centered modal on desktop
**Close:** X button (`aria-label="Close"`) top-right corner

### Modal UI Elements

| Element | Identifier Hint | Type | State |
|---|---|---|---|
| Title | "Welcome back" | `<h2>` | Static |
| Subtitle | "Sign in to continue to Mehad" | `<p>` | Static |
| Close button | `aria-label="Close"`, `data-slot="dialog-close"` | Button | Always |
| **WhatsApp Number** label | `text="WhatsApp Number"` | Label | Static |
| Country code selector | `aria-haspopup="listbox"`, `aria-label="Country code"` | Dropdown button | Default: 🇸🇦 +966 |
| Country search input | `placeholder="Search..."`, `type="text"` | Text input (inside dropdown) | Visible when dropdown open |
| Country option list | `role="listbox"` + `role="option"` items | Listbox | 81 countries |
| Phone number input | `type="tel"`, `placeholder="50 123 4567"`, `inputmode="numeric"`, `maxlength="12"`, `pattern="[0-9]{7,12}"` | Tel input | Required |
| **Send Code** button | `text="Send Code"` | Submit button | Disabled until phone entered |
| **Verification code** label | "Enter verification code" | Label | Static |
| OTP input | `type="text"`, `placeholder="000000"`, `autocomplete="one-time-code"`, `inputmode="numeric"`, `maxlength="6"` | OTP input | Disabled until code sent |
| Resend timer | "Resend in Xs" countdown | Text | Visible after code sent (60s cooldown) |
| **Continue** button | `text="Continue"` | Submit button | Disabled until OTP entered |
| Change number link | "Change Mobile Number" | Button/link | Visible after code sent |

### Country Code Dropdown Behaviour

- Default: 🇸🇦 Saudi Arabia +966
- Searchable: typing in the search field filters the 81-country list
- Selected flag + country code shown in the selector button
- Selection collapses the dropdown and updates the displayed code

---

## User Flows

### Flow 1: Successful Login (New Tutor / New Student)
```
1. User navigates to https://dev.mehadedu.com/en
2. Page loads — unauthenticated state; "Log In" button visible in header
3. User clicks "Log In" button
4. Login modal opens with title "Welcome back" — phone input and OTP input visible
5. User clicks country code selector → dropdown with search opens (default +966)
6. User types "Bangladesh" in search → filtered list shows "Bangladesh +880"
7. User clicks "Bangladesh +880" option → selector updates to 🇧🇩 +880
8. User enters phone number in tel field: 98976564
9. "Send Code" button becomes enabled; user clicks it
10. Modal updates: OTP input becomes enabled, "Resend in 60s" timer appears,
    "Code already sent" hint shows, "Change Mobile Number" link appears
11. User enters OTP: 123456 in the 6-digit verification field
12. "Continue" button becomes enabled; user clicks it
13. Modal closes; success toast "Logged in successfully!" appears
14. Header updates: "Log In" button replaced with user profile name ("Automations Student")
15. User is now authenticated on the homepage
```

**Test Credentials (Staging)**
```
Country code : +880 (Bangladesh)
Phone number : 98976564
OTP          : 123456
Role         : New Tutor / New Student
Expected name: Automations Student
```

### Flow 2: Search for a Tutor
```
1. User is on homepage (logged in or out)
2. User selects a Subject from the dropdown (e.g., Math)
3. Optionally selects Level, Available Time, Price Range
4. Clicks "Find a Teacher"
5. Browser navigates to /en/find-tutors with query params
6. Tutor listing page shows filtered results
```

### Flow 3: Browse Specific Subject
```
1. User clicks a subject badge in "STUDY SUBJECTS" section (e.g., Physics)
2. Browser navigates to /en/find-tutors?subjectId=3
3. Tutor listing pre-filtered by Physics appears
```

### Flow 4: Navigate to Tutor Profile
```
1. User sees a tutor card in the "Our Top Teachers" section
2. User clicks the card
3. Browser navigates to /en/tutor/{id}
4. Tutor profile page loads
```

### Flow 5: Language Switch (EN → AR)
```
1. User clicks "AR" button in the language switcher
2. Page reloads with Arabic locale (/ar)
3. All content switches to Arabic RTL layout
4. "EN" button becomes active
```

### Flow 6: Logout / Unauthenticated Access
```
1. Logged-in user clicks their profile avatar/name in the header
2. Dropdown appears with logout option (inferred)
3. User clicks Logout
4. Session cleared; header returns to "Log In" button state
```

### Flow 7: OTP Resend
```
1. After clicking "Send Code", user waits 60 seconds
2. "Resend in Xs" timer counts down to 0
3. "Resend Code" link/button becomes clickable
4. User clicks Resend — new OTP sent to WhatsApp
5. 60s cooldown restarts
```

---

## Validation Rules

### Country Code Selector
- Default: +966 (Saudi Arabia)
- Searchable — partial match on country name or dial code
- Stores selection; persists across modal interactions

### Phone Number Field
- Required — `Send Code` disabled until filled
- Type: `tel`, `inputmode="numeric"`
- Pattern: `[0-9]{7,12}`
- `maxlength="12"`
- Placeholder: "50 123 4567" (Saudi format hint)
- No letters or symbols accepted

### OTP Field
- Required — `Continue` disabled until filled
- Type: `text`, `inputmode="numeric"`, `autocomplete="one-time-code"`
- `maxlength="6"`, 6 digits only
- Disabled until `Send Code` succeeds
- Placeholder: "000000"
- Centered tracking-widest text display

### Send Code Button
- Disabled state: when phone field is empty or invalid
- Enabled state: when valid phone number entered
- Post-click: shows "Code already sent" tooltip; button may re-enable after cooldown

### Continue Button
- Disabled until OTP field has content
- Triggers authentication API call on click

---

## Edge Cases

| ID | Scenario | Expected Behavior |
|---|---|---|
| EC-M-01 | Phone field empty — click Send Code | Button stays disabled; no API call |
| EC-M-02 | Invalid phone format (letters, symbols) | Input rejects non-numeric; or shows validation error |
| EC-M-03 | Phone number < 7 digits | Send Code stays disabled (pattern validation) |
| EC-M-04 | Phone number > 12 digits | Input stops accepting after 12 chars (maxlength) |
| EC-M-05 | Incorrect OTP entered | Continue fails; error message shown; field clears or highlights |
| EC-M-06 | OTP entered after 60s expiry | Server rejects; error displayed |
| EC-M-07 | Resend clicked immediately (< 60s) | Resend link disabled during cooldown |
| EC-M-08 | Close modal mid-flow | Modal closes; no session created; re-opening resets state |
| EC-M-09 | "Change Mobile Number" clicked | OTP step collapses; user can re-enter a different phone |
| EC-M-10 | Country code not changed (wrong code for number) | OTP delivery may fail silently; user retries with correct code |
| EC-M-11 | Valid phone — wrong OTP 3× | Rate limit or lockout message expected |
| EC-M-12 | Already logged-in user accesses /en | "Log In" button not visible; user name shown instead |
| EC-M-13 | Login on mobile viewport (375px) | Modal renders as full-height drawer; inputs usable |
| EC-M-14 | Login with Arabic locale (/ar) | Modal content in Arabic; country selector defaults to +966 |
| EC-M-15 | Network failure during Send Code | User-friendly error message; no crash |
| EC-M-16 | Network failure during Continue | User-friendly error message; OTP not consumed |
| EC-M-17 | Tutor search with no filters selected | Find a Teacher navigates to /en/find-tutors with all tutors |
| EC-M-18 | Tutor search — all filters selected | Results filtered correctly |
| EC-M-19 | Language toggle on mobile | Reloads correct locale |
| EC-M-20 | Direct navigation to /ar | All content in Arabic RTL |

---

## API Contract (Inferred from Behaviour)

| Method | Endpoint | Trigger |
|---|---|---|
| POST | `/api/auth/send-otp` or similar | "Send Code" click |
| POST | `/api/auth/verify-otp` or similar | "Continue" click |
| GET | `/api/session` or cookie check | Page load (detect auth state) |
| GET | `/en/find-tutors?subjectId=X` | Tutor search or subject click |

### OTP Request (inferred)
```json
{
  "phone": "+88098976564",
  "countryCode": "+880",
  "localNumber": "98976564"
}
```

### OTP Verify Request (inferred)
```json
{
  "phone": "+88098976564",
  "otp": "123456"
}
```

### Verify Response — Success (200)
```json
{
  "token": "<jwt_or_session_token>",
  "user": {
    "name": "Automations Student",
    "role": "student"
  }
}
```

### Verify Response — Failure (401)
```json
{
  "error": "Invalid or expired OTP"
}
```

---

## Find Tutors Page — `/en/find-tutors`

### Filters
| Filter | Values |
|---|---|
| Subject | All Subjects (default), or specific subjects (Math, Physics, etc.) |
| Level | All Levels (default) |
| Price per lesson | Any price (default); range slider or select |
| Available times | Any time (default) |
| Search | Free-text — name or keyword |

### Tutor Card Elements
| Element | Example |
|---|---|
| Avatar | Initials or photo |
| Verified badge | "Verified" |
| Name | "Fahim Iqbal" |
| Star rating | "0.00 (0 Reviews)" |
| Subject | "Math" |
| Student count | "4 Students" |
| Lessons count | "0 lessons" |
| Languages | "Bengali, English" |
| Bio snippet | Short description |
| Trial lesson price | "Trial lesson from 50" |
| Hourly rate | "50 per hour" |
| Actions | Book Trial Lesson, Message, Save (bookmark) |

---

## Test Data

### Valid Login Credentials (Staging)
```
Country  : Bangladesh (+880)
Phone    : 98976564
OTP      : 123456
Expected : Login successful; user = "Automations Student"
Role     : New Tutor / New Student
```

### Invalid / Edge Case Inputs
```
Phone (too short)     : 123
Phone (non-numeric)   : abc@test
Phone (empty)         : (blank)
OTP (wrong)           : 000000
OTP (expired)         : any after 60s without resend
OTP (too short)       : 1234 (5 chars)
Country code (missing): form validation required
```

### Tutor Search Test Data
```
Subject : Math         → expects ~25 tutors
Subject : Physics      → expects ~9 tutors
Subject : Algebra      → expects ~12 tutors
Keyword : Fahim        → expects Fahim Iqbal result
Level   : Advanced     → filtered subset
```

---

## Expected Behaviors

### Success States
- Login: Toast "Logged in successfully!" appears; header shows user name within 1s
- Search: Tutor listing loads with correct filter applied
- Language switch: Page reloads with new locale; all content translated

### Error States
- Wrong OTP: Error message visible without full page reload
- Network timeout: User-friendly message (not raw HTTP status)
- Empty required field: Visual indicator on field; submit blocked

### Loading States
- Send Code: Button shows loading state during OTP dispatch
- Continue: Button shows loading state during verification
- Tutor search: Loading skeleton or spinner while results fetch

### Accessibility
- Modal: `role="dialog"`, `aria-modal="true"` expected; focus trapped inside
- Country selector: `aria-label="Country code"`, `aria-haspopup="listbox"`
- OTP field: `autocomplete="one-time-code"` for native autofill support
- Language buttons: `aria-label` with language name in that language
- Close button: `aria-label="Close"`
- Tab order (modal): Country code → Phone → Send Code → OTP → Continue → Close

---

## Related Pages

| Page | URL | Relationship |
|---|---|---|
| Find Tutors | `/en/find-tutors` | Primary CTA destination |
| Tutor Profile | `/en/tutor/{id}` | Tutor card links here |
| Become a Tutor | `/en/become-tutor` | Header + footer nav |
| How It Works | `/en/how-mehad-works` | Header + "HOW IT WORKS" section |
| About Us | `/en/about-us` | Header nav |
| Arabic locale | `/ar` | Language toggle destination |

---

## Coverage Gaps to Investigate

- [ ] SSO / Google OAuth login (if available)
- [ ] Magic link login alternative
- [ ] Session expiry — what happens after JWT/token expires
- [ ] Remember Me / persistent session behaviour
- [ ] Mobile app deep-link from WhatsApp OTP message
- [ ] Multi-device concurrent login
- [ ] Tutor registration flow (`/en/become-tutor`)
- [ ] Payment gateway integration (booking a lesson)
- [ ] Student dashboard after login
- [ ] Tutor dashboard after login with tutor role
- [ ] MFA or 2FA beyond OTP
- [ ] OTP delivery verification (WhatsApp vs SMS fallback)
- [ ] Cookie consent banner (not observed but may be present)
- [ ] GDPR / PDPL compliance notices
- [ ] Chatbot or live support widget
- [ ] Pricing page content (`/en/pricing` — in footer but not confirmed)

---

## Skip Directives — How to Tell the QA System What NOT to Test

The Fagun QA agent reads this section and automatically skips matching
tests. Use natural language; recognised verbs include **don't test**,
**skip**, **ignore**, **exclude**, **avoid testing**.

Example forms (uncomment to apply):

<!--
- Don't test phone responsiveness
- Skip i18n tests
- Ignore visual regression on this page
- Do not test OTP rate limiting
- Avoid testing cross-browser
-->

The system maps phrases to canonical test types — see
`ai_engine/spec_directives.py` for the full synonym table. When a
directive triggers, matching tests appear as **SKIPPED** in the report
with reason `skipped per spec directive: type='<name>'` so you always
know why.
