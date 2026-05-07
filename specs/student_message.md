Base URL

https://dev.mehadedu.com/en/dashboard/messages

Objective

Validate the full Messages module, including:

Sidebar navigation
Conversation list handling
Direct chat functionality
Message sending
Details panel actions
Base Steps (Given by User)
Login as a student
Click Profile icon from header section
Sidebar menu should open
Click on Messages from sidebar
Redirect to Messages page
Verify 3-panel layout loads:
Conversation list (left)
Direct chat (center)
Details panel (right)
Click on any conversation (e.g., Test Tutor)
Chat window should open
View previous messages
Send a message
Verify message appears in chat
Check Details panel updates correctly
UI Structure Validation (From Screenshot)
Left Panel (Sidebar Navigation)
My Bookings visible
Messages highlighted/active state
Favorite Teachers visible
Payments visible
Reviews & Ratings visible
Middle Panel (Conversation List)
Search Conversations input available
Tabs visible:
All
Unread
Archived
Conversation items show:
Profile icon
Name (e.g., Test Tutor)
Last message preview
Timestamp
Unread count badge (if any)
Center Panel (Direct Chat)
Header shows selected user name
Message bubbles displayed correctly
Input box available at bottom
Send button active
Attachment icon visible (if supported)
Right Panel (Details)
Tutor profile info visible
Rating / review section
Price per hour displayed
Action buttons:
Share
Archive
Book Lesson
Functional Test Scenarios
🔹 Navigation Validation
Clicking Messages opens correct route
URL matches /dashboard/messages
Sidebar active state highlights Messages
Switching between sidebar items preserves state correctly
🔹 Conversation List Validation
Conversations load successfully
Search filters conversations correctly
All / Unread / Archived tabs work properly
Clicking conversation loads correct chat
Unread badge updates correctly
🔹 Chat Window Validation
Selected conversation loads messages correctly
Previous chat history visible
Message alignment correct:
Sender → right
Receiver → left
Auto-scroll to latest message works
Time stamps displayed properly
🔹 Send Message Validation
Input field accepts text
Send button enabled only when text exists
Clicking send:
Message appears instantly
Input clears after sending
Prevent duplicate sends on rapid click
🔹 Message Input Validation
Empty message cannot be sent
Special characters supported
Long messages handled correctly
Input trims unnecessary spaces
🔹 Details Panel Validation
Correct tutor details displayed
Share button functional
Archive button moves conversation correctly
Book Lesson button redirects properly
Data updates when conversation changes
🔹 Search Functionality
Search filters conversations in real time
No match → empty state shown
Search resets properly
🔹 Archive Flow
Clicking Archive moves conversation to archived tab
Archived tab shows correct data
Archived conversation not visible in All tab
🔹 Error Handling
Failed message send shows error
Network failure shows retry option
Conversation load failure handled properly
🔹 Data Consistency
Messages stored correctly
No duplicate messages
Conversation order maintained
Sync between panels correct
🔹 Security Validation
Only authenticated users can access messages
Prevent unauthorized API access
Input sanitized (XSS prevention)
🔹 Performance
Conversation load < 3 seconds
Smooth scrolling in chat
No UI freeze during message send
🔹 Cross Browser Testing
Chrome supported
Firefox supported
Edge supported
Mobile responsive layout works
🔹 Accessibility
Keyboard navigation supported
Enter key sends message
Proper ARIA labels for inputs
Screen reader compatibility