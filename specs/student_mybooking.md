Student Booking & Session Flow Test Cases (Frontend)
Base Steps (Given by User)
Login as a student
Click Profile icon from header section
Sidebar menu should open
Click on My Bookings
Redirect to /dashboard/bookings page
View Upcoming Sessions
View Completed Sessions (Session History)
Match current time with session schedule
Click Join button for active session
Attend the session/class
After session end time → go to Upcoming
Click Complete Session button
Session moves to Completed Sessions / History
Additional Test Scenarios (Recommended)
🔹 UI / UX Validation
Profile icon visible in header
Sidebar opens smoothly after click
My Bookings menu visible and clickable
Proper layout for:
Upcoming Sessions
Completed Sessions
Session cards properly aligned
Buttons (Join, Complete) clearly visible
Responsive design for mobile/tablet
🔹 Navigation Validation
Clicking My Bookings redirects correctly
URL should be /dashboard/bookings
Page loads without errors
Back/refresh maintains correct state
🔹 Upcoming Session Validation
Only future sessions displayed
Sessions sorted by nearest time
Each session shows:
Title
Date & time
Status
Join button behavior:
Before time → disabled
On time → enabled
After time → hidden or disabled
🔹 Join Session Validation
Join button clickable only at valid time
Clicking Join:
Opens session/class page
Redirect works correctly
Prevent multiple clicks
Show loader while joining
🔹 Time-Based Logic Validation
System time must match session time
Edge cases:
Before time → cannot join
Exact time → join allowed
After time → join restricted
🔹 Complete Session Validation
Complete Session button visible after session ends
Clicking Complete:
Updates session status
Removes from Upcoming
Prevent multiple submissions
🔹 Completed Session (History) Validation
Completed sessions appear in history
Must include:
Session details
Completion status
Correct sorting (latest first recommended)
🔹 Data Consistency Validation
Session should not exist in both sections
No duplicate sessions
Data sync with backend
🔹 Error Handling
Failed session load → show error
Join failure → retry option
Complete action failure → proper message
🔹 Security Validation
Only logged-in users can access bookings
Unauthorized access redirects to login
Session links protected
🔹 Performance
Page load time < 3 seconds
Smooth UI interaction
No lag during join/complete actions
🔹 Cross Browser Testing
Chrome, Firefox, Edge support
Mobile browser compatibility
🔹 Accessibility
Keyboard navigation supported
Proper button labels
Screen reader compatibility
Bonus (Automation Scope)
Automate full flow using Playwright / Cypress
Validate:
Session fetch API
Join session API
Complete session API
Mock time for session validation
End-to-end flow testing
Notes
Test with different session times (past, present, future)
Verify timezone handling
Check session auto-expiry behavior
Ensure frontend and backend data consistency