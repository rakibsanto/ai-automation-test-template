# Dashboard Module Specification

## Module Name
Dashboard

## User Roles
- Company Owner
- Admin
- Agent

---

# 1. Access Control

## Authorized Users
The following users can access the dashboard:
- Company Owner
- Admin
- Agent

## Unauthorized Users
Unauthorized users must not be able to access dashboard content.

### Expected Behavior
- Redirect unauthorized users to login page
- Show access denied message if direct dashboard URL is accessed
- Dashboard data must not be visible

---

# 2. Welcome Message

When a Company Owner, Admin, or Agent logs into the system, the dashboard should display a dynamic welcome message based on the current system time.

## Time-Based Welcome Messages

### Morning
**Time Range:** 12:00 AM – 11:59 AM

**Message:**  
Good Morning

---

### Afternoon / Evening
**Time Range:** 12:00 PM – 7:59 PM

**Message:**  
Good Evening

---

### Night
**Time Range:** 8:00 PM – 11:59 PM

**Message:**  
Good Night

---

## Expected Behavior
- Message should update automatically based on login time
- Correct greeting should display for all roles
- Greeting should be visible immediately after login

---

# 3. Dashboard Statistics Cards

Users should be able to view the following statistical counts:

## Metrics
- Total Open Conversation Count
- Total Conversation Count
- New Contact Count
- Total Contact Count
- New Added Count
- Currently Active Count

---

## Filter Options

Dashboard statistics must support filtering by:

- Last 7 Days
- Last 30 Days
- Last 6 Months

---

## Expected Behavior
- Data updates immediately after selecting filter
- Correct values displayed for selected period
- Selected filter should remain highlighted

---

# 4. Broadcast Chart Section

Dashboard should display a broadcast analytics chart.

## Chart Metrics
- Total Sent Messages
- Total Delivered Messages
- Total Read Messages
- Total Failed Messages

---

## Filter Options
Users can filter chart data by:

- Last 7 Days
- Last 30 Days
- Last 6 Months

---

## Expected Behavior
- Chart updates dynamically when filter changes
- Data must match backend response
- Chart should render correctly without visual distortion

---

# 5. Message Summary Section

Dashboard should display message analytics summary.

## Message Metrics
- Total Messages
- Sent Messages
- Delivered Messages
- Read Messages
- Failed Messages

---

## Expected Behavior
- Counts should match backend data
- Values should refresh according to selected time period

---

# 6. Conversation by Agents Table

Dashboard should display a table named:

**Conversation by Agents**

---

## Table Data

The table should show:

### User Information
- Agent Name
- Admin Name

### Assigned Customer Status Counts
- Open
- Pending
- Close
- Rating

---

## Expected Behavior
- All agents and admins should be listed
- Correct conversation status counts should display
- Data should be role-specific and accurate

---

# 7. Pagination Rules

Pagination visibility depends on row count.

## Condition 1: Data ≤ 9
### Expected Behavior
Pagination should be hidden

---

## Condition 2: Data > 9
### Expected Behavior
Pagination should be visible

---

## Pagination Functionalities
- Next Page
- Previous Page
- Page Number Selection

---

# 8. Role-Based Dashboard Visibility

## Company Owner
Can view:
- Full dashboard data
- All agent/admin conversation metrics

---

## Admin
Can view:
- Dashboard statistics
- Assigned conversations
- Broadcast and message analytics

---

## Agent
Can view:
- Dashboard statistics
- Own assigned conversation metrics

---

# 9. Error Handling

## If Dashboard API Fails
Expected:
- Show error message
- Prevent broken UI rendering
- Retry option if applicable

---

# 10. UI Validation

Dashboard must ensure:

- Proper card alignment
- Correct chart rendering
- Responsive table layout
- No overlapping content
- Proper filter dropdown behavior

---

# 11. Security Validation

Ensure:
- Unauthorized users cannot access dashboard
- API endpoints are protected
- Role-based data restriction is enforced

---

# Acceptance Criteria

The feature is complete when:

- Correct welcome message appears based on login time
- All dashboard statistics display correctly
- Filters work properly
- Broadcast chart updates dynamically
- Message summary displays accurate data
- Conversation by Agents table works correctly
- Pagination behaves as expected
- Unauthorized users cannot access dashboard
- Role-based access is properly enforced

# 12. Detailed Test Scenarios

---

# 12.1 Welcome Message (Time-Based Greeting)

## Positive Test Cases
- User logs in at 8:00 AM → shows "Good Morning"
- User logs in at 2:00 PM → shows "Good Evening"
- User logs in at 9:00 PM → shows "Good Night"
- Owner/Admin/Agent all receive correct greeting based on time
- System clock time is used correctly

## Negative Test Cases
- Invalid system time → fallback message should appear
- API delay → dashboard should still render default UI
- Time zone mismatch → should not show incorrect greeting
- Unauthorized user tries to access → no greeting shown

## Edge Cases
- Login exactly at boundary (11:59 AM / 12:00 PM / 7:59 PM / 8:00 PM)
- Server time vs client time mismatch
- User logs in during daylight saving change (if applicable)
- Multiple logins within same minute

---

# 12.2 Dashboard Statistics Cards

## Positive Test Cases
- All counts display correctly for valid API response
- Filter “Last 7 Days” updates all metrics correctly
- Filter “Last 30 Days” shows correct aggregated data
- Filter “Last 6 Months” returns historical data correctly
- Data refresh works after page reload

## Negative Test Cases
- API returns null → show 0 or fallback state
- API failure → show error or empty state
- Partial data missing (e.g., missing active users) → handle gracefully
- Invalid filter selection → no crash

## Edge Cases
- Very large numbers (e.g., 999999+ counts)
- Zero activity period (all values = 0)
- Rapid filter switching (7 days → 30 days → 6 months quickly)
- Network slow response during filter change

---

# 12.3 Broadcast Chart Section

## Positive Test Cases
- Sent, delivered, read, failed messages displayed correctly
- Chart updates correctly for all filters
- Data matches backend response exactly
- Chart renders properly on page load

## Negative Test Cases
- Missing dataset → chart should not crash
- Backend returns incorrect keys → fallback handling
- No broadcast data → empty state shown
- API timeout → loading state remains visible

## Edge Cases
- All messages failed (100% failure scenario)
- All messages read instantly
- Extremely high message volume causing chart scaling issues
- Switching filters rapidly while chart is loading

---

# 12.4 Message Summary Section

## Positive Test Cases
- Total messages count matches sum of all statuses
- Sent, delivered, read, failed counts are accurate
- Filter updates message stats correctly

## Negative Test Cases
- Missing message data → fallback to zero
- API inconsistency between summary and broadcast data
- Duplicate messages counted incorrectly

## Edge Cases
- Delivered > Sent (data inconsistency scenario)
- Read count higher than delivered (invalid backend data)
- Huge dataset causing UI lag

---

# 12.5 Conversation by Agents Table

## Positive Test Cases
- All agents and admins are listed correctly
- Open, Pending, Close, Rating values displayed properly
- Pagination works when data > 9
- Table updates correctly with API response

## Negative Test Cases
- Empty agent list → show “No data available”
- Missing status fields → show default value (0 or N/A)
- API failure → table fallback state
- Invalid role data → prevent UI crash

## Edge Cases
- Exactly 9 records → pagination hidden
- 10+ records → pagination visible and functional
- Agents with no assigned customers
- One agent with extremely high assigned count
- Mixed role duplication (same user as admin + agent)

---

# 12.6 Pagination Behavior

## Positive Test Cases
- Pagination visible when records > 9
- Pagination hidden when records ≤ 9
- Next/Previous buttons work correctly
- Page number selection works properly

## Negative Test Cases
- Clicking disabled pagination buttons does nothing
- Invalid page number in URL handled safely
- API returns fewer items than expected page size

## Edge Cases
- Data exactly at boundary (9 → 10 records)
- Single page only scenario
- Last page has fewer records than page size
- Very large dataset (1000+ agents)

---

# 12.7 Unauthorized Access

## Positive Test Cases
- Unauthorized user redirected to login
- Token validation blocks dashboard access
- Role mismatch prevents access

## Negative Test Cases
- Manipulated token bypass attempt should fail
- Direct URL access should not show data
- Cached dashboard page should not load after logout

## Edge Cases
- Token expires during dashboard session
- Multiple tab session logout synchronization
- Slow API response after session expiry

---

# 12.8 Role-Based Access Control

## Positive Test Cases
- Owner sees full dashboard
- Admin sees permitted analytics only
- Agent sees only assigned data

## Negative Test Cases
- Agent tries to access admin data → blocked
- Admin tries owner-only metrics → restricted
- Role tampering in frontend → ignored by backend

## Edge Cases
- User has multiple roles (admin + agent)
- Role change during active session
- Partial role permission loading delay

---