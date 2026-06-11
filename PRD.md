# Product Requirements Document (PRD)
## ChicCherry — E-Commerce Platform

**Version:** 1.0  
**Platform:** Web (Django)  
**Market:** Bangladesh  

---

## 1. Product Overview

ChicCherry is an online fashion and lifestyle e-commerce platform. It allows customers to browse, filter, and purchase products with OTP-verified checkout, while giving administrators full control over the catalogue, orders, and reviews through a custom admin panel.

---

## 2. User Types

| User Type | Description |
|---|---|
| **Guest** | Unauthenticated visitor browsing the store |
| **Registered Customer** | Verified account holder who can purchase and review |
| **Admin / Superadmin** | Staff with access to the custom admin panel |

---

## 3. Guest User

### 3.1 Goals
- Browse products without creating an account
- Search and filter products
- View product details and reviews

### 3.2 Features

#### Home Page
- Banner carousel with promotional images
- Popular products section (8 products)
- Popular footwear section
- Category navigation dropdown

#### Store / Product Listing
- Paginated product grid (3 per page)
- Filter by size (dynamic, checkbox chips)
- Filter by price range (min/max)
- Filter by category (via URL slug)
- Keyword search
- Product count display

#### Product Detail
- Product images (main + gallery)
- Description, price, stock
- Color and size variation selectors
- Visible approved reviews with ratings
- Average star rating display

#### Account
- Register with email, name, phone
- OTP email verification (10-minute expiry) to activate account
- Login with email + password
- Forgot password via email token reset

### 3.3 Constraints
- Cannot add to cart (redirected to login)
- Cannot submit reviews
- Cannot access dashboard or order history

---

## 4. Registered Customer

### 4.1 Goals
- Purchase products with variation selection
- Track orders and manage profile
- Submit reviews for purchased products

### 4.2 Features

#### Cart
- Add products with color/size variations
- Cart persists across sessions
- Cart merges with session cart on login
- Quantity increment/decrement
- Remove individual items
- Subtotal, 2% tax, grand total calculation
- AJAX cart count update in navbar

#### Checkout
- **Step 1 — Shipping Form:** First name, last name, phone, email, address, city, state, country, order note, additional info. Pre-filled from profile for logged-in users.
- **Step 2 — OTP Verification:** 6-digit OTP sent to email, 10-minute expiry, must verify before order is placed.
- Order number auto-generated from date + ID
- Shipping address saved back to user profile

#### Payment
- Select from: Visa, Mastercard, Rocket, bKash, Upay, Nogod
- Enter account number or use saved account
- Account number validation per method (digit length rules)
- Saved payment accounts per method (masked display)
- Order confirmation email sent on payment

#### Order Management
- Order history list with status badges
- Order detail: items, variations, pricing, shipping address
- Status timeline: Placed → Processing → Shipped → Delivered / Cancelled
- Order status update log with timestamps

#### Profile & Account
- Dashboard: order count, profile summary
- Edit profile: name, phone, address, profile picture
- Change password (requires current password)
- Logout

#### Reviews
- Submit review only after purchasing the product
- Rate (float), subject, review text, optional image
- Rate limiting: max 3 reviews per hour
- Review pending moderation before visible
- Update existing review
- Email confirmation on submission

### 4.3 Constraints
- Must be email-verified to log in
- Cannot access admin panel
- Cannot review products not purchased

---

## 5. Admin / Superadmin

### 5.1 Goals
- Manage the full product catalogue
- Process and track orders
- Moderate reviews
- Manage users and categories

### 5.2 Features

#### Dashboard (`/secureadmin/`)
- Stat cards: total orders, products, users, revenue
- Monthly revenue bar chart (last 12 months)
- Recent 8 orders table with status and payment badges
- Quick navigation sidebar

#### Sidebar Navigation
- Dashboard
- Accounts / Users
- Products / Add Product
- Add Variation Category
- Categories
- Orders
- Reviews
- Settings (change password)
- View Store (opens store with header hidden)

#### Product Management
- Add/edit/delete products
- Fields: name, slug (auto), description, price, stock, main image, category, availability
- **Variations inline:** add unlimited variations per product (category dropdown + value), dynamic categories via `VariationCategory` model
- **Gallery inline:** add unlimited additional product images
- Prepopulated slug from product name

#### Variation Category Management
- Add custom variation categories (e.g., color, size, material, brand)
- Used as dropdown in product variation inline
- Replaces hardcoded choices

#### Category Management
- Add/edit/delete categories with slug, description, image

#### Order Management
- List all orders with filters
- View order details, items, shipping
- Update order status
- Payment status tracking

#### Review Moderation
- List all reviews with filters (visibility, rating, date, purchase verified)
- Approve reviews (makes visible to customers)
- Reject reviews (hides from customers)
- Full audit trail per review (who approved/rejected, when, notes)
- Read-only review fields to prevent tampering

#### User Management
- List all accounts
- View/edit user details
- Activate/deactivate accounts

### 5.3 Constraints
- Admin panel at `/secureadmin/` (not `/admin/`)
- Only `is_admin=True` users can access
- Superadmin has full permissions

---

## 6. Email Notifications

| Trigger | Recipient | Content |
|---|---|---|
| Registration | Customer | OTP verification code |
| OTP resend | Customer | New OTP code |
| Checkout | Customer | OTP for order verification |
| Order placed | Customer | Order confirmation + items |
| Payment confirmed | Customer | Payment receipt + order details |
| Review submitted | Customer | Review pending moderation notice |
| Password reset | Customer | Reset link |

Primary: Node.js Nodemailer service. Fallback: Django SMTP with exponential backoff retry (3 attempts).

---

## 7. Non-Functional Requirements

| Requirement | Detail |
|---|---|
| Security | Custom admin URL, OTP verification, purchase-gated reviews, rate limiting |
| Media Storage | Local (`media/`) in dev; MinIO-compatible for production |
| Pagination | 3 products per page with preserved filter params |
| Responsiveness | Bootstrap 4 responsive grid |
| SEO | Slug-based product and category URLs |
| Audit | Review audit trail, order status history |

---

## 8. Data Models Summary

```
Account ──────────── UserProfile
    │
    ├── CartItem ──── Cart
    │       └── Variation (M2M)
    │
    ├── Order ──────── OrderItem ──── Product ──── Category
    │       │               └── Variation (M2M)       │
    │       └── OrderStatusUpdate                      └── ProductGallery
    │
    ├── ReviewRating ── ReviewAudit                Variation ──── VariationCategory
    │       └── HelpfulnessVote
    │
    └── PaymentAccount
```

---

## 9. Out of Scope (v1.0)

- Real payment gateway integration (currently simulated)
- Multi-vendor support
- Wishlist / saved items
- Product comparison
- Discount codes / coupons
- Mobile app
