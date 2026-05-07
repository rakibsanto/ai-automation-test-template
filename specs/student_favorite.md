Base URL

https://dev.mehadedu.com/en/dashboard/favorites

Objective

Validate the Favorite Teachers module, including:

Add/remove favorite tutors
View favorite tutor list
Book lesson from favorites
Browse and search other tutors
Base Steps (Given by User)
Login as a student
Click Profile icon from header
Sidebar menu should open
Click on Favorite Teachers
Redirect to Favorite Teachers page
View list of favorite tutors
Click heart icon to remove a tutor from favorites
Click heart icon again to re-add tutor
Click Book Lesson button
Redirect to booking flow
Browse more tutors from button
Search and view other tutors
UI Structure Validation (From Screenshot)
Sidebar Navigation
My Bookings visible
Messages visible
Favorite Teachers highlighted (active state)
Payments visible
Reviews & Ratings visible
Favorite Teachers Page Layout
Page title: Favorite Teachers
Tutor cards displayed properly
Each tutor card includes:
Profile image/avatar
Tutor name (e.g., Test Tutor)
Badge (Professional)
Rating
Number of lessons
Language
Hourly rate
Book Lesson button
Heart icon (favorite toggle)
Functional Test Scenarios
🔹 Add to Favorites
Click heart icon on tutor card
Expected:
Tutor added to favorites list
Heart becomes filled (active state)
UI updates instantly
🔹 Remove from Favorites
Click filled heart icon
Expected:
Tutor removed from favorites
Heart becomes empty
Tutor disappears from list (or updates state)
🔹 Toggle Favorite State
Multiple click test on heart icon
Expected:
State should toggle correctly
No duplicate entries
No UI glitch
🔹 Book Lesson Flow
Click Book Lesson button
Expected:
Redirect to booking/session page
Tutor selected automatically
Booking flow starts correctly
🔹 Browse More Tutors
Click Browse more tutors button
Expected:
Redirect to tutor listing page
All available tutors displayed
User can search/select new tutors
🔹 Navigation Validation
Sidebar navigation works correctly
Favorite Teachers page loads without errors
URL matches /dashboard/favorites
🔹 Data Consistency
Favorite list persists after refresh
Removed tutor does not reappear
Added tutor stays in list
Sync with backend maintained
🔹 UI / UX Validation
Heart icon clearly visible on card
Active/inactive state distinguishable
Book Lesson button accessible
Card layout responsive
Hover/click feedback smooth
🔹 Error Handling
Failed add/remove favorite → show error message
Network failure → retry option
Booking failure → proper fallback message
🔹 Performance
Favorite list loads within 3 seconds
Toggle favorite action is instant
No UI lag when updating state
🔹 Security Validation
Only logged-in users can modify favorites
Unauthorized access redirects to login
API should validate user ownership
🔹 Cross Browser Testing
Chrome supported
Firefox supported
Edge supported
Mobile responsive behavior verified
🔹 Accessibility
Heart icon accessible via keyboard
Proper aria-label for favorite toggle
Book Lesson button screen-reader friendly