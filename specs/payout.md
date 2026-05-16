# Super Admin Payout Flow (End-to-End Process)

## 1. Login Success Process
- The Super Admin will log in successfully
- Authentication will be validated
- After successful login, the dashboard will load

---

## 2. Navigate to Payout Section
- Click on the **"Payout"** option from the sidebar
- After clicking, a **Dialog / Modal** will open

---

## 3. Payout Dashboard Cards
There will be a total of 4 cards at the top of the dialog:

1. Total Help
2. Pending Payouts
3. Total Payouts
4. Total Refunds *(Currently NOT enabled / Not available)*

👉 Currently focus on:
- Total Help
- Pending Payouts
- Total Payouts

---

## 4. Pending Payouts Logic
The Pending Payouts section will display:

- Tutor Name
- Completed Sessions Count
- Requested Payout Amount
- Date Range
- Fees Breakdown
  - Platform Fee included in fee calculation
- Status (Pending / Approved)
- Actions Button

---

## 5. Action Flow (Approve Process)
In the Action column, there will be:

### Options:
- Approve Button
- Three Dot Menu (⋮)

### After Approval:
- Pending → Paid status will be updated
- Amount will be added to Total Paid
- Total Held will be updated

---

## 6. View Details (Three Dot Menu)
- “View Session Details” option will be available
- It will show full payout breakdown:
  - Sessions list
  - Tutor details
  - Fee calculation
  - Date-wise breakdown

---

## 7. Manual Trigger Button (IMPORTANT)
- A **Manual Trigger Button** will be available
- It will be used to simulate/test new payout requests

### Verification points:
- Check if new payout requests are being created
- Check if amount calculation is correct
- Check if entries are properly added to the Pending list

---

## 8. Tutor Profile Validation
- Visit Tutor Profile
- Verify:
  - Payout deduction is correct
  - Session count matches
  - Earnings are updating properly

---

## 9. End-to-End Verification Flow
✔ Login → Dashboard → Payout  
✔ Request generation (manual + system)  
✔ Pending state verification  
✔ Approval flow  
✔ Paid state update  
✔ Tutor profile sync  

---

## 10. Final Goal
- All payout requests should correctly reach the Super Admin
- After Super Admin approval, the system should automatically update:
  - Tutor side
  - Admin side
  - Reports / totals