# Translation Management (Dynamic Localization System)

## Overview

The Translation module is a **dynamic localization system** managed by the Super Admin.

This system allows:
- Multi-language support (English, Arabic, etc.)
- Dynamic key-value based translations
- Role-based translation (Admin, Student, Tutor, Public)
- App-wide translation control
- Subject-wise and feature-wise translation support

### Key Concept
A single translation entry works across the entire system dynamically based on:
- Language
- App/Role
- Group
- Key

---

# Open Translation Module

1. Login as Super Admin.
2. Open the **Sidebar**.
3. Go to **Account Settings**.
4. Click on **Translation** card.

---

# Search Translation

1. Use **Search by Key or Value** field.
2. Enter:
   - Translation Key
   - Translation Value
3. System should return matching results.

---

# Language Filter

Available filters:
- English
- Arabic

## Behavior
- Selecting a language filters translations based on that language.

---

# App Filter (Role-Based)

Available apps/roles:
- Admin
- Student
- Tutor
- Public

## Behavior
- Translations can be filtered based on application role.
- Each role may have different UI text rendering.

---

# Group Filter

Available groups:
- Platform Fee
- Translation (General)

## Behavior
- Filters translations by category/group.
- Helps organize large-scale translation data.

---

# Clear Filters

- Resets all applied filters.
- Restores default translation list view.

---

# Translation Actions

Each translation entry supports:

## View
- View full translation details.

## Edit
- Modify:
  - Key
  - English translation
  - Arabic translation
  - Group
  - App/Role

## Delete
- Remove translation entry from system.

---

# Create Translation

## Step 1: Language Selection
- Select source and target language.

---

## Step 2: App Selection
Choose where translation will be applied:
- Admin
- Student
- Tutor
- Public

---

## Step 3: Group Selection
Assign to a group:
- Platform Fee
- Translation Group (or others)

---

## Step 4: Key Definition
- Enter translation key from codebase.

---

## Step 5: Translation Values

### English Translation
- Enter English text.

### Arabic Translation
- Enter Arabic text (if applicable)

---

# Create Process

1. Fill all required fields.
2. Click **Create Translation**.
3. Translation becomes active in the system.

---

# Dynamic Behavior

After creation:

- Translation is automatically applied across the system.
- UI text changes based on:
  - Selected language
  - Role (Admin/Student/Tutor/Public)
  - Group mapping

---

# Verification & Testing

## Search Test
- Key-based search works correctly
- Value-based search works correctly

## Language Test
- English/Arabic switching works properly

## Role-Based Test
- Admin sees admin translations
- Student sees student UI translations
- Tutor sees tutor-specific translations

## Group Test
- Platform Fee translations grouped correctly
- General translations appear properly

## Action Test
- Edit updates reflect immediately
- Delete removes translation properly

## System Integration Test
- All modules reflect correct translations dynamically:
  - Homepage
  - Dashboard
  - Forms
  - Buttons
  - Labels

---

# Final Expected Behavior

- Fully dynamic multilingual system
- No hardcoded UI text dependency
- Real-time translation updates across platform
- Role-based UI text rendering