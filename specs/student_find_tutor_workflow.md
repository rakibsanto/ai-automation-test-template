# One-to-One and Group Session Booking Process - MehaEdu

## Steps to Reproduce One-to-One Session Booking

### 1. Navigate to Website
- Open the MehaEdu website: [https://dev.mehadedu.com/en].

### 2. Student Login
- Log in as a student using valid credentials.

### 3. Access Find Tutors
- After login, go to the header section and click the "Find Tutors" button.

### 4. Select One-to-One Session
- Choose the "One-to-One Session" option from the dropdown.

### 5. Book Lesson
- Select a tutor and choose a slot.
- Click "Book Lesson."
- Packages will be displayed.

### 6. Select Package
- Choose a package that suits your needs.
- Click "Continue."

### 7. Apply Promo Code (Optional)
- If you have a promo code, enter it and click "Apply."
- If no promo code, just proceed by clicking "Confirm and Pay."

### 8. Complete Payment
- Enter payment details: cardholder name, card number, expiry date, security code.
- Click "Pay Now."
- A confirmation modal will open; click "Submit."

### 9. Redirect to My Bookings
- After submission, you will be redirected to "My Bookings."
- In "My Bookings," you will see your purchased package.
- Since hours are sold per package, you will allocate the specific number of slots (hours) you purchased.
- After selecting the slot, click "Continue and Confirm."
- Your slot will be booked.

---

## Steps for Group Session Booking

### 1. Navigate to Website
- Open the MehaEdu website: [Insert Website URL Here].

### 2. Student Login
- Log in as a student using valid credentials.

### 3. Access Find Tutors
- After login, click the "Find Tutors" button in the header.

### 4. Select Group Session
- Choose the "Group Session" option from the dropdown.

### 5. Filter Courses
- Use the filter to select the subject, price per lesson, available times, or tutor’s first name.

### 6. Enroll in Course
- After reviewing results, click "Enroll."

### 7. Logical Constraint
- Ensure you do not enroll in the same course more than once.
- If already enrolled, the system should prevent a second booking for the same course.

### 8. Complete Payment
- Once enrolled, proceed to the payment gateway.
- Enter your cardholder name, card number, expiry date, and security code.
- Click "Pay Now."
- Confirm via the modal by clicking "Submit."

### 9. Verify in My Bookings
- After payment, check "My Bookings" to see the enrolled course.
- Each slot booked corresponds to hours purchased, so you must allocate your hours within the package.

---

## Notes
- Ensure logical validation prevents duplicate enrollment in group sessions.
- Confirm that each slot booking is unique per student and course.
- Test that once enrolled, no duplicate bookings for the same course are allowed.