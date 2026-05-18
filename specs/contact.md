# Contact Module Specification

## Module Name
Contact Management

## User Roles
- Company Owner
- Admin
- Agent

---

# 1. Access Control

## Authorized Users
The following users can access the contacts page:
- Company Owner
- Admin
- Agent (Role-based data restriction may apply)

## Unauthorized Users
Unauthorized users must not be able to access contact data.

### Expected Behavior
- Redirect unauthorized users to login page
- Show access denied message if direct URL is accessed
- Contact data must not be visible

---

# 2. Contact List Table

The main contacts page should display a table containing all available contacts.

## Table Columns
- Name
- Phone Number
- Email
- Tags/Groups
- Status
- Actions (Edit, Delete, View)

## Expected Behavior
- Display all authorized contacts in a responsive table format.
- Action buttons must be fully functional.

---

# 3. Add Contact

Users should be able to add new contacts to the system manually.

## Required Fields
- Name
- Phone Number (with Country Code)

## Optional Fields
- Email
- Tags
- Notes

## Expected Behavior
- "Add Contact" button opens a modal or new page.
- Validation for phone number format.
- Success message upon creation.
- Table updates with the new contact immediately.

---

# 4. Import / Export Contacts

Users should be able to bulk import and export contact data.

## Import
- Allowed formats: `.csv`, `.xlsx`
- Mapping interface to map file columns to database fields.
- Error reporting for invalid rows.

## Export
- Formats: `.csv`, `.xlsx`
- Export current view (filtered) or all contacts.

---

# 5. Search and Filters

Users should be able to quickly find specific contacts.

## Search Capabilities
- Click on the name search field and enter a name that automatically search the contacts name
- Click on the phone search field and enter a phone numner that automatically search the contacts phone

## Filter Options
- Filter by Tags/Groups
- Filter by Status
- Filter by Date Added

## Expected Behavior
- Table updates dynamically as the user types or selects filters.
- Clear button to reset all filters.

---

# 6. Edit and Delete Contact

## Edit functionality
- Clicking 'Edit' allows modification of all fields.
- Save changes dynamically updates the list.

## Delete functionality
- Clicking 'Delete' triggers a confirmation prompt.
- Soft delete or hard delete depending on application rules.
- Table updates upon successful deletion.

---

# 7. Pagination Rules

Pagination visibility depends on the total row count.

## Condition 1: Data ≤ 10
### Expected Behavior
Pagination should be hidden or disabled.

---

## Condition 2: Data > 10
### Expected Behavior
Pagination should be visible and functional.

## Pagination Functionalities
- Next Page
- Previous Page
- Page Number Selection
- Rows per page dropdown (10, 25, 50, 100)

---

# 8. Error Handling

## Expected Behavior
- Show validation errors for incorrect phone formats or duplicate entries.
- Show a user-friendly error message if the API fails to load data.
- Handle network timeouts gracefully without breaking UI.

---

# 9. Acceptance Criteria

The feature is complete when:
- Contacts list renders correctly with data from the backend.
- Adding a new contact works and updates the list.
- Search and filters correctly refine the list of contacts.
- Editing and deleting work correctly with proper confirmations.
- Import/Export functionality accurately processes `.csv`/`.xlsx` files.
- Unauthorized access is blocked.

---

# 10. Detailed Test Scenarios

---

# 10.1 Contact List View
## Positive Test Cases
- Verify the list renders correctly with data from the API.
- Verify column headers are correct.
## Negative Test Cases
- API failure shows empty state or error message.

# 10.2 Add Contact
## Positive Test Cases
- Create contact with all valid data.
- Create contact with only required fields.
## Negative Test Cases
- Leave required fields blank.
- Enter invalid phone number format.
- Attempt to create a duplicate contact.

# 10.3 Search and Filter
## Positive Test Cases
- Search by exact name, partial name, and phone number.
- Apply a tag filter and verify results.
## Negative Test Cases
- Search string with no matches displays "No results found".

# 10.4 Edit & Delete
## Positive Test Cases
- Successfully update a contact's phone number.
- Successfully delete a contact after confirming the prompt.
## Negative Test Cases
- Cancel a delete action and ensure the contact remains.

# 10.5 Import/Export
## Positive Test Cases
- Import a valid CSV with 10 contacts.
- Export current list and verify file contents.
## Negative Test Cases
- Import CSV with invalid phone formats.
- Upload an unsupported file type (.pdf).

# 10.6 Pagination
## Positive Test Cases
- Navigate to the next page and verify data updates.
- Change rows per page and verify count.
