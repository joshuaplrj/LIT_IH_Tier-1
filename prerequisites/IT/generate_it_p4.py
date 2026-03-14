"""
generate_it_p4.py
Generates all prerequisite files for IT-P4: AccessibilityAI
Creates 5 test websites with deliberate WCAG 2.2 violations + ground_truth.json
"""

import os
import json

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IT-P4")
SITES_DIR = os.path.join(BASE_DIR, "test_websites")
os.makedirs(BASE_DIR, exist_ok=True)
for i in range(1, 6):
    os.makedirs(os.path.join(SITES_DIR, f"site_{i}"), exist_ok=True)

# ─── Site 1: E-commerce product page ─────────────────────────────────────────
# Violations: missing alt text, low contrast, unlabeled input, non-descriptive link, autoplay video

site1_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ShopEasy - Premium Wireless Headphones</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <div class="logo">ShopEasy</div>
    <nav>
      <a href="/">Home</a>
      <a href="/products">Products</a>
      <a href="/cart">Cart (0)</a>
    </nav>
  </header>

  <main class="product-page">
    <div class="product-gallery">
      <!-- VIOLATION 1 (1.1.1): Missing alt text on product images -->
      <img src="product.jpg" class="product-img" width="500" height="400">
      <img src="product-side.jpg" class="product-img-thumb">
      <img src="product-back.jpg" class="product-img-thumb">
    </div>

    <div class="product-details">
      <h1>Premium Wireless Headphones X900</h1>

      <!-- VIOLATION 2 (1.4.3): Low contrast — #999 on white fails 4.5:1 ratio -->
      <p class="low-contrast-price">Was $299.99</p>
      <p class="price">$199.99</p>
      <p class="low-contrast-text">Free delivery on orders over $50. Limited stock available.</p>

      <div class="rating">
        <span>★★★★☆</span>
        <span class="review-count low-contrast-text">(1,243 reviews)</span>
      </div>

      <div class="product-subscribe">
        <h2>Get notified when back in stock</h2>
        <!-- VIOLATION 3 (1.3.1 / 4.1.2): Input without associated label -->
        <input type="email" placeholder="Enter your email" class="email-input">
        <button type="submit" class="btn-primary">Notify Me</button>
      </div>

      <div class="actions">
        <button class="btn-primary btn-large">Add to Cart</button>
        <!-- VIOLATION 4 (2.4.6 / 2.4.4): Non-descriptive link text -->
        <a href="/products/headphones-x900-details" class="details-link">click here</a>
        <a href="/wishlist/add?id=900" class="wishlist-link">click here</a>
      </div>

      <div class="product-description">
        <h2>Product Description</h2>
        <p>Experience crystal-clear audio with our flagship wireless headphones.
        40-hour battery life, active noise cancellation, and premium comfort.</p>
      </div>
    </div>

    <!-- VIOLATION 5 (1.4.2): Auto-playing video without controls -->
    <div class="product-video-section">
      <h2>See It In Action</h2>
      <video src="promo.mp4" autoplay loop class="promo-video">
        Your browser does not support the video tag.
      </video>
    </div>

    <section class="related-products">
      <h2>Related Products</h2>
      <div class="product-grid">
        <div class="product-card">
          <!-- Also missing alt -->
          <img src="related1.jpg" class="product-img">
          <p>Sport Earbuds Z10</p>
          <p class="price">$89.99</p>
          <a href="/products/z10">click here</a>
        </div>
        <div class="product-card">
          <img src="related2.jpg" class="product-img">
          <p>Studio Monitor S5</p>
          <p class="price">$349.99</p>
          <a href="/products/s5">click here</a>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <p class="low-contrast-text">&copy; 2024 ShopEasy. All rights reserved.</p>
  </footer>
</body>
</html>
"""

site1_css = """/* Site 1 — E-commerce product page */
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: Arial, sans-serif;
  color: #333;
  background: #fff;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  background: #1a1a2e;
  color: #fff;
}

header nav a { color: #fff; text-decoration: none; margin-left: 24px; }

.product-page {
  max-width: 1200px;
  margin: 32px auto;
  padding: 0 16px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
}

.product-gallery img.product-img { width: 100%; border-radius: 8px; }
.product-img-thumb { width: 80px; height: 80px; object-fit: cover; margin-right: 8px; }

.product-details { display: flex; flex-direction: column; gap: 16px; }

h1 { font-size: 1.8rem; }
h2 { font-size: 1.3rem; }

/* VIOLATION 2: Low contrast — #999999 on #ffffff gives ~2.85:1 ratio (fails 4.5:1) */
.low-contrast-text { color: #999999; font-size: 0.9rem; }
.low-contrast-price { color: #999999; text-decoration: line-through; font-size: 1rem; }

.price { font-size: 1.6rem; font-weight: bold; color: #e63946; }

.btn-primary {
  background: #1a1a2e;
  color: #fff;
  border: none;
  padding: 12px 24px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}
.btn-large { padding: 16px 32px; font-size: 1.1rem; }

.email-input {
  padding: 10px 14px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
  width: 260px;
}

.details-link, .wishlist-link {
  display: inline-block;
  margin-left: 16px;
  color: #1a1a2e;
}

/* VIOLATION 5: autoplay video — no controls attribute in HTML */
.promo-video { width: 100%; border-radius: 8px; }
.product-video-section { grid-column: 1 / -1; }

.product-grid { display: flex; gap: 24px; }
.product-card { width: 200px; }
.product-card img { width: 100%; }
.related-products { grid-column: 1 / -1; }

footer { background: #f5f5f5; text-align: center; padding: 24px; margin-top: 48px; }
"""

# ─── Site 2: News article page ────────────────────────────────────────────────
# Violations: improper heading hierarchy (h1->h4), no lang attribute, color-only error, keyboard trap

site2_html = """<!DOCTYPE html>
<!-- VIOLATION 2 (3.1.1): Missing lang attribute on <html> element -->
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>City Herald - Breaking News</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="site-header">
    <div class="masthead">The City Herald</div>
    <nav class="main-nav">
      <a href="/">Home</a>
      <a href="/world">World</a>
      <a href="/tech">Technology</a>
      <a href="/sports">Sports</a>
      <a href="/opinion">Opinion</a>
    </nav>
  </header>

  <!-- VIOLATION 3 (1.4.1): Color used as only means to convey information -->
  <div class="breaking-banner color-only-error">
    BREAKING: City council announces emergency infrastructure budget
  </div>

  <main class="article-container">
    <article>
      <!-- VIOLATION 1 (1.3.1 / 2.4.6): Heading hierarchy jumps from h1 to h4 -->
      <h1 class="article-title">City Council Approves $2.4 Billion Infrastructure Overhaul</h1>

      <div class="article-meta">
        <span>By Jane Morrison</span>
        <span>March 14, 2026</span>
        <span class="category-label">Local Government</span>
      </div>

      <img src="city-council.jpg" alt="City council chamber during the vote session" class="hero-image">

      <!-- Skips h2, h3 — jumps directly to h4 -->
      <h4 class="section-heading">Key Highlights of the Budget</h4>

      <p>The city council voted 8-3 in favor of the largest infrastructure investment in the
      city's history. The plan includes major upgrades to roads, bridges, public transit,
      and digital infrastructure over the next decade.</p>

      <h4 class="section-heading">Transportation Improvements</h4>

      <p>Mayor David Chen called the vote "a historic moment for our city." The transportation
      component alone accounts for $1.1 billion, addressing decades of deferred maintenance
      on the city's aging bridge network.</p>

      <h4 class="section-heading">Public Reaction</h4>

      <p>Residents have had mixed reactions. Supporters argue the investment is long overdue,
      while critics express concern over the tax implications for small businesses.</p>

      <!-- Color-only error indicator — no icon or text label, just red color -->
      <div class="comment-section">
        <h4>Leave a Comment</h4>
        <form class="comment-form">
          <div class="field-group">
            <label for="comment-name">Name</label>
            <input type="text" id="comment-name" name="name">
            <!-- Error shown only in color — red text, no icon, no "Error:" prefix -->
            <span class="color-only-error" id="name-error" hidden>This field is required</span>
          </div>
          <div class="field-group">
            <label for="comment-email">Email</label>
            <input type="email" id="comment-email" name="email">
            <span class="color-only-error" id="email-error" hidden>Enter a valid email address</span>
          </div>
          <div class="field-group">
            <label for="comment-text">Comment</label>
            <textarea id="comment-text" name="comment" rows="4"></textarea>
          </div>
          <!-- Subscribe button opens a modal with a keyboard trap -->
          <button type="button" class="btn-secondary" onclick="openModal()">Subscribe to Newsletter</button>
          <button type="submit" class="btn-primary">Post Comment</button>
        </form>
      </div>
    </article>

    <aside class="sidebar">
      <h4>Trending Stories</h4>
      <ul>
        <li><a href="/story/1">Tech company announces 500 new jobs</a></li>
        <li><a href="/story/2">Local school wins national award</a></li>
        <li><a href="/story/3">Weather alert: Heavy rain expected</a></li>
      </ul>
    </aside>
  </main>

  <!-- VIOLATION 4 (2.1.2): Keyboard trap modal — no Escape key handling, focus loops inside but cannot exit -->
  <div id="newsletter-modal" class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" style="display:none;">
    <div class="modal-overlay"></div>
    <div class="modal-content">
      <h2 id="modal-title">Subscribe to The City Herald</h2>
      <p>Get the latest news delivered to your inbox every morning.</p>
      <div class="field-group">
        <label for="modal-email">Email Address</label>
        <input type="email" id="modal-email" name="modal-email">
      </div>
      <!-- No close button, no Escape key handler — keyboard trap -->
      <button type="button" class="btn-primary" onclick="submitSubscription()">Subscribe</button>
    </div>
  </div>

  <footer>
    <p>&copy; 2026 The City Herald. All rights reserved.</p>
  </footer>

  <script>
    function openModal() {
      var modal = document.getElementById('newsletter-modal');
      modal.style.display = 'flex';
      // VIOLATION 4: Focus is set to modal but there is no way to close it with keyboard.
      // No keydown listener for Escape, no close button — keyboard trap.
      document.getElementById('modal-email').focus();
      // Deliberately trap focus inside modal without escape route
      modal.addEventListener('keydown', function(e) {
        // Intentionally does NOT handle Escape key to create a keyboard trap
        if (e.key === 'Tab') {
          var focusable = modal.querySelectorAll('input, button');
          var first = focusable[0];
          var last = focusable[focusable.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
        // Escape key NOT handled — user cannot leave modal with keyboard
      });
    }
    function submitSubscription() {
      alert('Subscribed!');
    }
  </script>
</body>
</html>
"""

site2_css = """/* Site 2 — News article */
* { box-sizing: border-box; margin: 0; padding: 0; }

body { font-family: Georgia, serif; color: #222; background: #fff; }

.site-header {
  background: #1c2b3a;
  color: #fff;
  padding: 16px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.masthead { font-size: 1.8rem; font-weight: bold; letter-spacing: 2px; }
.main-nav a { color: #ccc; text-decoration: none; margin-left: 20px; }

/* VIOLATION 3: Error/alert communicated through color alone — no icon, no text prefix */
.color-only-error { color: #cc0000; }
.breaking-banner {
  background: #fff3cd;
  padding: 12px 40px;
  font-weight: bold;
  font-size: 0.95rem;
  /* Red text is the ONLY signal that this is urgent/error state */
}

.article-container {
  max-width: 1100px;
  margin: 32px auto;
  padding: 0 20px;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 48px;
}

.article-title { font-size: 2rem; line-height: 1.3; margin-bottom: 16px; }
.article-meta { color: #555; font-size: 0.9rem; margin-bottom: 20px; }
.article-meta span { margin-right: 16px; }
.category-label { background: #1c2b3a; color: #fff; padding: 2px 8px; border-radius: 3px; }

.hero-image { width: 100%; height: 320px; object-fit: cover; border-radius: 4px; margin-bottom: 24px; }

/* VIOLATION 1: h4 used after h1, skipping h2 and h3 */
.section-heading { font-size: 1.3rem; margin: 24px 0 12px; }

p { line-height: 1.7; margin-bottom: 16px; }

.comment-section { margin-top: 40px; border-top: 2px solid #eee; padding-top: 24px; }
.comment-section h4 { font-size: 1.2rem; margin-bottom: 20px; }

.field-group { margin-bottom: 16px; }
.field-group label { display: block; font-size: 0.9rem; margin-bottom: 6px; font-weight: bold; }
.field-group input, .field-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
}

.btn-primary {
  background: #1c2b3a; color: #fff;
  border: none; padding: 10px 24px;
  border-radius: 4px; cursor: pointer;
  font-size: 1rem;
}
.btn-secondary {
  background: #e8e8e8; color: #333;
  border: none; padding: 10px 24px;
  border-radius: 4px; cursor: pointer;
  font-size: 1rem; margin-right: 12px;
}

.sidebar { border-left: 1px solid #e0e0e0; padding-left: 24px; }
.sidebar h4 { font-size: 1.1rem; margin-bottom: 16px; }
.sidebar ul { list-style: none; }
.sidebar li { margin-bottom: 12px; border-bottom: 1px solid #f0f0f0; padding-bottom: 12px; }
.sidebar a { color: #1c2b3a; text-decoration: none; font-size: 0.95rem; }

/* VIOLATION 4: Modal with keyboard trap */
.modal {
  position: fixed; top: 0; left: 0;
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); }
.modal-content {
  position: relative; background: #fff;
  padding: 32px; border-radius: 8px;
  max-width: 460px; width: 90%;
  z-index: 1;
}
.modal-content h2 { margin-bottom: 12px; }
/* Note: No visible X/close button — trap reinforced by missing close mechanism */

footer { background: #1c2b3a; color: #999; text-align: center; padding: 24px; margin-top: 48px; }
"""

# ─── Site 3: Government form page ─────────────────────────────────────────────
# Violations: table without headers, required fields not marked, error in color only,
# custom checkbox no ARIA role, PDF link no file type indication

site3_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Municipal Services Portal - License Application</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="gov-header">
    <div class="gov-logo">
      <img src="govt-seal.png" alt="City of Greenville Official Seal">
      <div>
        <h1>City of Greenville</h1>
        <p>Municipal Services Portal</p>
      </div>
    </div>
    <nav>
      <a href="/">Home</a>
      <a href="/services">Services</a>
      <a href="/contact">Contact</a>
    </nav>
  </header>

  <main class="form-container">
    <h2>Business License Application</h2>
    <p>Complete the form below to apply for a new business operating license.</p>

    <!-- VIOLATION 1 (1.1.1 / 1.3.1): Table without th headers -->
    <section class="fee-schedule">
      <h3>License Fee Schedule</h3>
      <!-- No <thead> or <th> elements — screen readers cannot associate data with columns -->
      <table class="fee-table">
        <tr>
          <td>Business Type</td>
          <td>Annual Fee</td>
          <td>Processing Time</td>
          <td>Renewal Period</td>
        </tr>
        <tr>
          <td>Retail</td>
          <td>$250</td>
          <td>5-7 business days</td>
          <td>Annually (Jan 31)</td>
        </tr>
        <tr>
          <td>Food Service</td>
          <td>$400</td>
          <td>10-14 business days</td>
          <td>Annually (Jan 31)</td>
        </tr>
        <tr>
          <td>Professional Services</td>
          <td>$175</td>
          <td>3-5 business days</td>
          <td>Annually (Jan 31)</td>
        </tr>
        <tr>
          <td>Manufacturing</td>
          <td>$600</td>
          <td>15-20 business days</td>
          <td>Annually (Jan 31)</td>
        </tr>
      </table>
    </section>

    <form id="license-form" novalidate>
      <fieldset>
        <legend>Business Information</legend>

        <!-- VIOLATION 2 (3.3.2): Required fields not marked — no asterisk, no aria-required -->
        <div class="form-group">
          <label for="biz-name">Business Name</label>
          <input type="text" id="biz-name" name="biz-name">
          <!-- No required attribute, no visual indicator of required status -->
        </div>

        <div class="form-group">
          <label for="biz-type">Business Type</label>
          <select id="biz-type" name="biz-type">
            <option value="">-- Select Type --</option>
            <option value="retail">Retail</option>
            <option value="food">Food Service</option>
            <option value="professional">Professional Services</option>
            <option value="manufacturing">Manufacturing</option>
          </select>
        </div>

        <div class="form-group">
          <label for="ein">Employer Identification Number (EIN)</label>
          <input type="text" id="ein" name="ein" placeholder="XX-XXXXXXX">
        </div>

        <div class="form-group">
          <label for="biz-address">Business Address</label>
          <input type="text" id="biz-address" name="biz-address">
        </div>
      </fieldset>

      <fieldset>
        <legend>Owner Information</legend>

        <div class="form-group">
          <label for="owner-name">Owner Full Name</label>
          <input type="text" id="owner-name" name="owner-name">
        </div>

        <div class="form-group">
          <label for="owner-email">Email Address</label>
          <input type="email" id="owner-email" name="owner-email">
          <!-- VIOLATION 3 (1.4.1 / 3.3.1): Error shown only in red color, no text like "Error:" -->
          <span class="error-msg color-error" id="email-error" aria-hidden="true" style="display:none;">
            Please enter a valid email address
          </span>
        </div>

        <div class="form-group">
          <label for="owner-phone">Phone Number</label>
          <input type="tel" id="owner-phone" name="owner-phone" placeholder="(555) 555-5555">
        </div>
      </fieldset>

      <fieldset>
        <legend>Declarations</legend>

        <!-- VIOLATION 4 (4.1.2): Custom checkbox div with no ARIA role or keyboard support -->
        <div class="form-group">
          <div class="custom-checkbox" onclick="toggleCheck(this)" tabindex="0">
            <div class="check-indicator"></div>
            <span>I certify that all information provided is accurate and complete</span>
          </div>
          <!-- No role="checkbox", no aria-checked, no keyboard Enter/Space handler -->
        </div>

        <div class="form-group">
          <div class="custom-checkbox" onclick="toggleCheck(this)" tabindex="0">
            <div class="check-indicator"></div>
            <span>I agree to the terms and conditions of the business license</span>
          </div>
        </div>

        <!-- VIOLATION 5 (1.1.1): PDF link without file type/size indication -->
        <p>Please review the
          <!-- No "(PDF)" or file size indication in the link or surrounding text -->
          <a href="/docs/license-terms.pdf" class="doc-link">Terms and Conditions</a>
          before submitting.
        </p>
      </fieldset>

      <div class="form-actions">
        <button type="button" class="btn-secondary" onclick="saveDraft()">Save Draft</button>
        <button type="submit" class="btn-primary" onclick="submitForm(event)">Submit Application</button>
      </div>
    </form>
  </main>

  <footer class="gov-footer">
    <p>City of Greenville &bull; 123 Main Street &bull; Greenville &bull; 555-0100</p>
    <p>&copy; 2026 City of Greenville. All rights reserved.</p>
  </footer>

  <script>
    function toggleCheck(el) {
      el.classList.toggle('checked');
    }
    function saveDraft() {
      alert('Draft saved.');
    }
    function submitForm(e) {
      e.preventDefault();
      var email = document.getElementById('owner-email').value;
      var errEl = document.getElementById('email-error');
      if (email && !email.includes('@')) {
        // VIOLATION 3: Shows error only with red color, no programmatic role="alert" or "Error:" prefix
        errEl.style.display = 'block';
      } else {
        errEl.style.display = 'none';
        alert('Application submitted.');
      }
    }
  </script>
</body>
</html>
"""

site3_css = """/* Site 3 — Government form */
* { box-sizing: border-box; margin: 0; padding: 0; }

body { font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a1a; background: #f4f6f9; }

.gov-header {
  background: #003366;
  color: #fff;
  padding: 16px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.gov-logo { display: flex; align-items: center; gap: 16px; }
.gov-logo img { width: 60px; height: 60px; }
.gov-logo h1 { font-size: 1.4rem; }
.gov-logo p { font-size: 0.85rem; color: #aac4e0; }
.gov-header nav a { color: #aac4e0; text-decoration: none; margin-left: 20px; font-size: 0.95rem; }

.form-container {
  max-width: 860px;
  margin: 32px auto;
  background: #fff;
  padding: 40px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.form-container h2 { font-size: 1.6rem; color: #003366; margin-bottom: 8px; }

/* VIOLATION 1: Table without headers — no <th> elements */
.fee-table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0 32px;
}
.fee-table tr { border-bottom: 1px solid #ddd; }
.fee-table td { padding: 10px 14px; font-size: 0.95rem; }
.fee-table tr:first-child td { background: #003366; color: #fff; font-weight: bold; }
/* Note: first row uses <td> not <th> — this is the violation */

fieldset {
  border: 1px solid #d0d8e4;
  border-radius: 4px;
  padding: 24px;
  margin-bottom: 24px;
}
legend {
  font-weight: bold;
  color: #003366;
  font-size: 1.1rem;
  padding: 0 8px;
}

.form-group { margin-bottom: 20px; }
.form-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 6px;
  font-size: 0.95rem;
  /* VIOLATION 2: No asterisk (*) or "(required)" text next to required fields */
}
.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #aab;
  border-radius: 4px;
  font-size: 1rem;
  background: #fafbfc;
}
.form-group input:focus,
.form-group select:focus {
  border-color: #003366;
  outline: 2px solid #6699cc;
}

/* VIOLATION 3: Error displayed in red color only — no icon, no "Error:" text, no role="alert" */
.color-error { color: #cc0000; font-size: 0.85rem; margin-top: 4px; display: block; }
/* The error message itself says the issue but the MECHANISM of identification is color-only */

/* VIOLATION 4: Custom checkbox — div styled as checkbox but no ARIA role */
.custom-checkbox {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
  padding: 4px;
  /* No role="checkbox" and no aria-checked attribute in HTML */
}
.check-indicator {
  width: 20px;
  height: 20px;
  border: 2px solid #003366;
  border-radius: 3px;
  flex-shrink: 0;
  margin-top: 2px;
  background: #fff;
}
.custom-checkbox.checked .check-indicator {
  background: #003366;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath fill='white' d='M13.7 4.3l-8 8-3.4-3.4 1.4-1.4 2 2 6.6-6.6z'/%3E%3C/svg%3E");
}
/* VIOLATION 5: PDF link with no file type indication */
.doc-link { color: #003366; }

.form-actions { display: flex; justify-content: flex-end; gap: 16px; margin-top: 16px; }

.btn-primary {
  background: #003366; color: #fff;
  border: none; padding: 12px 28px;
  border-radius: 4px; cursor: pointer; font-size: 1rem;
}
.btn-secondary {
  background: #e8edf3; color: #003366;
  border: 1px solid #003366; padding: 12px 28px;
  border-radius: 4px; cursor: pointer; font-size: 1rem;
}

.gov-footer {
  background: #003366; color: #aac4e0;
  text-align: center; padding: 24px;
  margin-top: 0; font-size: 0.9rem; line-height: 1.8;
}
"""

# ─── Site 4: Healthcare portal ────────────────────────────────────────────────
# Violations: session timeout without warning, complex chart no text alt, small click targets

site4_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MediConnect Patient Portal</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="portal-header">
    <div class="header-left">
      <img src="logo.png" alt="MediConnect Logo" class="logo">
      <span class="portal-name">MediConnect Patient Portal</span>
    </div>
    <nav class="header-nav">
      <a href="/dashboard">Dashboard</a>
      <a href="/appointments">Appointments</a>
      <a href="/records">Records</a>
      <a href="/messages">Messages</a>
      <a href="/logout">Sign Out</a>
    </nav>
  </header>

  <main class="portal-content">
    <div class="welcome-banner">
      <h1>Welcome back, Sarah Johnson</h1>
      <p>Last login: March 13, 2026 at 9:42 AM</p>
    </div>

    <div class="dashboard-grid">
      <section class="card upcoming-appointments">
        <h2>Upcoming Appointments</h2>
        <ul class="appointment-list">
          <li>
            <div class="appt-date">Mar 20</div>
            <div class="appt-info">
              <strong>Dr. Maria Santos</strong>
              <span>General Check-up &bull; 10:00 AM</span>
              <span>Greenville Medical Center, Room 214</span>
            </div>
            <!-- VIOLATION 3: Small click targets — buttons smaller than 24×24 px -->
            <div class="appt-actions">
              <button class="tiny-btn" title="Reschedule">R</button>
              <button class="tiny-btn" title="Cancel">X</button>
            </div>
          </li>
          <li>
            <div class="appt-date">Apr 5</div>
            <div class="appt-info">
              <strong>Dr. Robert Kim</strong>
              <span>Cardiology Follow-up &bull; 2:30 PM</span>
              <span>Heart Health Clinic, Suite 400</span>
            </div>
            <div class="appt-actions">
              <button class="tiny-btn" title="Reschedule">R</button>
              <button class="tiny-btn" title="Cancel">X</button>
            </div>
          </li>
        </ul>
      </section>

      <section class="card health-metrics">
        <h2>Health Metrics — Last 6 Months</h2>
        <!-- VIOLATION 2 (1.1.1): Complex chart with no text alternative or data table -->
        <div class="chart-container">
          <!-- Canvas-based chart with no accessible description, no role, no aria-label beyond generic -->
          <canvas id="health-chart" width="520" height="260"></canvas>
          <!-- No <figcaption>, no summary table, no aria-describedby pointing to data -->
        </div>
      </section>

      <section class="card medications">
        <h2>Current Medications</h2>
        <table class="med-table">
          <thead>
            <tr>
              <th>Medication</th>
              <th>Dosage</th>
              <th>Frequency</th>
              <th>Prescribing Doctor</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Lisinopril</td>
              <td>10mg</td>
              <td>Once daily</td>
              <td>Dr. Kim</td>
            </tr>
            <tr>
              <td>Metformin</td>
              <td>500mg</td>
              <td>Twice daily with meals</td>
              <td>Dr. Santos</td>
            </tr>
            <tr>
              <td>Atorvastatin</td>
              <td>20mg</td>
              <td>Once daily at bedtime</td>
              <td>Dr. Kim</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="card recent-results">
        <h2>Recent Test Results</h2>
        <ul class="results-list">
          <li>
            <span class="result-name">Complete Blood Count</span>
            <span class="result-date">Feb 28, 2026</span>
            <span class="result-status normal">Normal</span>
            <button class="view-btn">View Results</button>
          </li>
          <li>
            <span class="result-name">Lipid Panel</span>
            <span class="result-date">Feb 28, 2026</span>
            <span class="result-status review">Needs Review</span>
            <button class="view-btn">View Results</button>
          </li>
          <li>
            <span class="result-name">HbA1c</span>
            <span class="result-date">Jan 15, 2026</span>
            <span class="result-status normal">Normal</span>
            <button class="view-btn">View Results</button>
          </li>
        </ul>
      </section>
    </div>
  </main>

  <!-- VIOLATION 1 (2.2.1): Session timeout fires without any accessible warning -->
  <!-- No aria-live region announces the timeout, no dialog warns the user beforehand -->
  <div id="timeout-overlay" style="display:none;" class="timeout-screen">
    <div class="timeout-box">
      <h2>Session Expired</h2>
      <p>Your session has expired due to inactivity. Please log in again to continue.</p>
      <a href="/login" class="btn-primary">Log In Again</a>
    </div>
  </div>
  <!-- Note: There is no aria-live="assertive" warning before timeout, no countdown dialog -->

  <footer class="portal-footer">
    <p>MediConnect &copy; 2026 &bull; HIPAA Compliant &bull; <a href="/privacy">Privacy Policy</a></p>
  </footer>

  <script>
    // VIOLATION 1: Session timeout without prior accessible warning
    // Session expires after 5 minutes of inactivity with NO warning to the user
    var sessionTimeout = setTimeout(function() {
      // Directly show expired screen without any prior warning notification
      // No aria-live announcement, no countdown dialog, no option to extend
      document.getElementById('timeout-overlay').style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }, 5 * 60 * 1000);

    // VIOLATION 2: Chart rendered on canvas with no text alternative
    var ctx = document.getElementById('health-chart').getContext('2d');
    // Simple canvas drawing — no accessible table, no aria-label with data summary
    ctx.fillStyle = '#e8f4fd';
    ctx.fillRect(0, 0, 520, 260);
    ctx.strokeStyle = '#2874a6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    var points = [[0,180],[80,160],[160,140],[240,155],[320,130],[400,120],[520,110]];
    ctx.moveTo(points[0][0], points[0][1]);
    for(var i=1;i<points.length;i++) ctx.lineTo(points[i][0], points[i][1]);
    ctx.stroke();
    ctx.fillStyle = '#2874a6';
    ctx.font = '13px Arial';
    ctx.fillText('Blood Pressure Trend (mmHg)', 10, 20);
    ctx.fillStyle = '#888';
    ctx.font = '11px Arial';
    ctx.fillText('Sep  Oct  Nov  Dec  Jan  Feb  Mar', 20, 250);
  </script>
</body>
</html>
"""

site4_css = """/* Site 4 — Healthcare portal */
* { box-sizing: border-box; margin: 0; padding: 0; }

body { font-family: 'Segoe UI', sans-serif; background: #f0f4f8; color: #1a1a2e; }

.portal-header {
  background: #1565c0;
  color: #fff;
  padding: 14px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.header-left { display: flex; align-items: center; gap: 14px; }
.logo { width: 40px; height: 40px; }
.portal-name { font-size: 1.1rem; font-weight: 600; }
.header-nav a { color: #bbdefb; text-decoration: none; margin-left: 20px; font-size: 0.9rem; }
.header-nav a:hover { color: #fff; }

.portal-content { max-width: 1100px; margin: 28px auto; padding: 0 20px; }

.welcome-banner {
  background: #fff;
  border-left: 4px solid #1565c0;
  padding: 16px 24px;
  border-radius: 4px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.welcome-banner h1 { font-size: 1.4rem; color: #1565c0; }
.welcome-banner p { color: #555; font-size: 0.9rem; }

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
.card h2 { font-size: 1.1rem; color: #1565c0; margin-bottom: 16px; border-bottom: 1px solid #e3e8f0; padding-bottom: 10px; }

.appointment-list { list-style: none; }
.appointment-list li {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f4f8;
}
.appt-date {
  background: #1565c0; color: #fff;
  border-radius: 4px; padding: 6px 10px;
  font-size: 0.85rem; text-align: center;
  min-width: 48px;
}
.appt-info { flex: 1; display: flex; flex-direction: column; gap: 2px; font-size: 0.9rem; }
.appt-actions { display: flex; gap: 4px; align-items: center; }

/* VIOLATION 3: Buttons smaller than 24×24 px minimum target size */
.tiny-btn {
  width: 18px;
  height: 18px;
  font-size: 9px;
  background: #e0e0e0;
  border: 1px solid #bbb;
  border-radius: 2px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  /* WCAG 2.5.8 requires minimum 24×24 CSS pixels — these are 18×18 */
}

.chart-container { width: 100%; overflow: hidden; }

.med-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.med-table th { background: #e8f0fb; color: #1565c0; text-align: left; padding: 8px 10px; }
.med-table td { padding: 8px 10px; border-bottom: 1px solid #f0f4f8; }

.results-list { list-style: none; }
.results-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f4f8;
  font-size: 0.9rem;
}
.result-name { flex: 1; font-weight: 500; }
.result-date { color: #777; font-size: 0.85rem; }
.result-status.normal { color: #2e7d32; font-weight: 600; }
.result-status.review { color: #e65100; font-weight: 600; }
.view-btn {
  background: transparent; border: 1px solid #1565c0;
  color: #1565c0; padding: 4px 10px; border-radius: 3px;
  cursor: pointer; font-size: 0.8rem;
}

/* VIOLATION 1: Session timeout overlay with no prior accessible warning */
.timeout-screen {
  position: fixed; top: 0; left: 0;
  width: 100%; height: 100%;
  background: rgba(0,0,0,0.75);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
}
.timeout-box {
  background: #fff; padding: 40px; border-radius: 8px;
  text-align: center; max-width: 400px;
}
.timeout-box h2 { color: #c62828; margin-bottom: 12px; }
.timeout-box p { margin-bottom: 24px; color: #555; }
.btn-primary {
  background: #1565c0; color: #fff;
  padding: 12px 28px; border-radius: 4px;
  text-decoration: none; font-size: 1rem;
  display: inline-block;
}

.portal-footer {
  text-align: center; background: #1565c0; color: #bbdefb;
  padding: 16px; font-size: 0.85rem; margin-top: 40px;
}
.portal-footer a { color: #fff; }
"""

# ─── Site 5: Education platform ───────────────────────────────────────────────
# Violations: flashing content (>3 Hz), audio no transcript, image of text heading,
# focus not visible (outline:none), carousel no pause/stop

site5_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LearnSphere - Online Learning Platform</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="edu-header">
    <a href="/" class="header-logo-link">
      <img src="learnsphere-logo.png" alt="LearnSphere" class="header-logo">
    </a>
    <nav class="edu-nav">
      <a href="/courses">Courses</a>
      <a href="/paths">Learning Paths</a>
      <a href="/community">Community</a>
      <a href="/dashboard">My Dashboard</a>
    </nav>
    <div class="header-actions">
      <button class="btn-outline">Log In</button>
      <button class="btn-primary">Sign Up Free</button>
    </div>
  </header>

  <main>
    <!-- VIOLATION 1 (2.3.1): Flashing element that flashes more than 3 times per second -->
    <div class="flash-banner" role="banner">
      <span class="flash-text">FLASH SALE — 70% OFF ALL COURSES THIS WEEKEND ONLY</span>
    </div>

    <!-- VIOLATION 3 (1.1.1): Image of text used as heading instead of real HTML text -->
    <section class="hero-section">
      <!-- Heading is rendered as an image, not accessible text -->
      <img src="hero-heading.png" class="hero-heading-img" alt="">
      <!-- alt="" means screen readers skip it entirely — heading content lost -->
      <p class="hero-subtitle">Master in-demand skills with expert-led courses. Join 2 million learners worldwide.</p>
      <div class="hero-cta">
        <button class="btn-primary btn-large">Explore Courses</button>
        <button class="btn-outline btn-large">Watch Demo</button>
      </div>
    </section>

    <!-- VIOLATION 5 (2.2.2): Carousel without pause / stop / hide controls -->
    <section class="featured-courses">
      <h2>Featured Courses</h2>
      <div class="carousel-wrapper">
        <div class="carousel" id="course-carousel">
          <div class="carousel-track" id="carousel-track">
            <div class="course-card">
              <img src="course-python.jpg" alt="Python for Data Science course thumbnail">
              <div class="course-info">
                <span class="course-tag">Data Science</span>
                <h3>Python for Data Science</h3>
                <p>4.8 ★ &bull; 42,000 students</p>
                <span class="course-price">$49.99</span>
              </div>
            </div>
            <div class="course-card">
              <img src="course-ux.jpg" alt="UX Design Fundamentals course thumbnail">
              <div class="course-info">
                <span class="course-tag">Design</span>
                <h3>UX Design Fundamentals</h3>
                <p>4.7 ★ &bull; 28,000 students</p>
                <span class="course-price">$39.99</span>
              </div>
            </div>
            <div class="course-card">
              <img src="course-react.jpg" alt="React Development Bootcamp course thumbnail">
              <div class="course-info">
                <span class="course-tag">Web Dev</span>
                <h3>React Development Bootcamp</h3>
                <p>4.9 ★ &bull; 61,000 students</p>
                <span class="course-price">$59.99</span>
              </div>
            </div>
            <div class="course-card">
              <img src="course-ml.jpg" alt="Machine Learning A-Z course thumbnail">
              <div class="course-info">
                <span class="course-tag">AI & ML</span>
                <h3>Machine Learning A-Z</h3>
                <p>4.6 ★ &bull; 55,000 students</p>
                <span class="course-price">$69.99</span>
              </div>
            </div>
            <div class="course-card">
              <img src="course-pm.jpg" alt="Product Management Masterclass course thumbnail">
              <div class="course-info">
                <span class="course-tag">Business</span>
                <h3>Product Management Masterclass</h3>
                <p>4.7 ★ &bull; 19,000 students</p>
                <span class="course-price">$44.99</span>
              </div>
            </div>
          </div>
          <!-- VIOLATION 5: No pause/stop button for the auto-advancing carousel -->
          <button class="carousel-btn prev" onclick="prevSlide()">&#8249;</button>
          <button class="carousel-btn next" onclick="nextSlide()">&#8250;</button>
          <!-- Missing: pause/stop button for users who need to stop motion -->
        </div>
      </div>
    </section>

    <!-- VIOLATION 2 (1.2.1): Audio content without a transcript -->
    <section class="instructor-message">
      <h2>A Message From Our Lead Instructor</h2>
      <div class="audio-player">
        <!-- Audio provided but no transcript, no captions equivalent for audio-only content -->
        <audio controls src="instructor-welcome.mp3">
          Your browser does not support the audio element.
        </audio>
        <!-- No transcript link, no collapsible transcript, no text equivalent -->
        <p class="audio-description">Listen to Dr. Chen's welcome message (2:34)</p>
      </div>
    </section>

    <section class="learning-paths">
      <h2>Popular Learning Paths</h2>
      <div class="paths-grid">
        <div class="path-card">
          <div class="path-icon">&#128187;</div>
          <h3>Full-Stack Developer</h3>
          <p>12 courses &bull; 6 months</p>
          <!-- VIOLATION 4: focus not visible — outline removed globally in CSS -->
          <a href="/paths/full-stack" class="path-link">Start Path</a>
        </div>
        <div class="path-card">
          <div class="path-icon">&#128202;</div>
          <h3>Data Analyst</h3>
          <p>8 courses &bull; 4 months</p>
          <a href="/paths/data-analyst" class="path-link">Start Path</a>
        </div>
        <div class="path-card">
          <div class="path-icon">&#129504;</div>
          <h3>Machine Learning Engineer</h3>
          <p>15 courses &bull; 9 months</p>
          <a href="/paths/ml-engineer" class="path-link">Start Path</a>
        </div>
        <div class="path-card">
          <div class="path-icon">&#127774;</div>
          <h3>UX/UI Designer</h3>
          <p>10 courses &bull; 5 months</p>
          <a href="/paths/ux-ui" class="path-link">Start Path</a>
        </div>
      </div>
    </section>
  </main>

  <footer class="edu-footer">
    <div class="footer-content">
      <div class="footer-col">
        <h4>LearnSphere</h4>
        <p>Empowering learners worldwide with quality education.</p>
      </div>
      <div class="footer-col">
        <h4>Courses</h4>
        <a href="/courses/tech">Technology</a>
        <a href="/courses/design">Design</a>
        <a href="/courses/business">Business</a>
      </div>
      <div class="footer-col">
        <h4>Company</h4>
        <a href="/about">About Us</a>
        <a href="/careers">Careers</a>
        <a href="/press">Press</a>
      </div>
    </div>
    <div class="footer-bottom">
      <p>&copy; 2026 LearnSphere Inc. All rights reserved.</p>
    </div>
  </footer>

  <script>
    // VIOLATION 5: Auto-advancing carousel with no pause control
    var currentSlide = 0;
    var totalSlides = 5;
    var carouselInterval = setInterval(function() {
      currentSlide = (currentSlide + 1) % totalSlides;
      document.getElementById('carousel-track').style.transform =
        'translateX(-' + (currentSlide * 280) + 'px)';
    }, 2000);
    // No pause/stop mechanism provided to users

    function prevSlide() {
      currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
      document.getElementById('carousel-track').style.transform =
        'translateX(-' + (currentSlide * 280) + 'px)';
    }
    function nextSlide() {
      currentSlide = (currentSlide + 1) % totalSlides;
      document.getElementById('carousel-track').style.transform =
        'translateX(-' + (currentSlide * 280) + 'px)';
    }
  </script>
</body>
</html>
"""

site5_css = """/* Site 5 — Education platform */
* { box-sizing: border-box; margin: 0; padding: 0; }

/* VIOLATION 4 (2.4.7): Focus indicator removed globally — keyboard users cannot see focus */
* { outline: none; }
/* This removes focus outlines from ALL interactive elements — links, buttons, inputs */

body { font-family: 'Inter', Arial, sans-serif; color: #1a1a2e; background: #fff; }

.edu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 40px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-logo { height: 36px; }
.header-logo-link { display: flex; }
.edu-nav a { color: #374151; text-decoration: none; margin: 0 16px; font-size: 0.95rem; }
.edu-nav a:hover { color: #4f46e5; }
.header-actions { display: flex; gap: 12px; }

.btn-primary {
  background: #4f46e5; color: #fff;
  border: none; padding: 10px 22px;
  border-radius: 6px; cursor: pointer;
  font-size: 0.95rem; font-weight: 500;
}
.btn-outline {
  background: transparent; color: #4f46e5;
  border: 2px solid #4f46e5; padding: 9px 22px;
  border-radius: 6px; cursor: pointer;
  font-size: 0.95rem; font-weight: 500;
}
.btn-large { padding: 14px 32px; font-size: 1.05rem; }

/* VIOLATION 1 (2.3.1): Flash animation — flashes at ~5 Hz (200ms cycle = 5 times/sec > 3Hz limit) */
@keyframes flashSale {
  0%   { background: #ff3b30; color: #fff; }
  49%  { background: #ff3b30; color: #fff; }
  50%  { background: #fff; color: #ff3b30; }
  99%  { background: #fff; color: #ff3b30; }
  100% { background: #ff3b30; color: #fff; }
}
.flash-banner {
  text-align: center;
  padding: 12px;
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: 0.5px;
  /* Flashing at 5 Hz — exceeds the 3 Hz threshold (WCAG 2.3.1) */
  animation: flashSale 0.2s infinite;
}

/* VIOLATION 3: Hero heading is an image of text */
.hero-section {
  text-align: center;
  padding: 80px 40px 60px;
  background: linear-gradient(135deg, #ede9fe 0%, #e0e7ff 100%);
}
.hero-heading-img {
  max-width: 700px;
  width: 80%;
  /* This renders styled heading text as an image — screen readers
     get alt="" so the heading is completely invisible to AT users */
}
.hero-subtitle {
  font-size: 1.15rem;
  color: #4b5563;
  margin: 20px auto 32px;
  max-width: 560px;
}
.hero-cta { display: flex; gap: 16px; justify-content: center; }

.featured-courses { padding: 48px 40px; }
.featured-courses h2 { font-size: 1.5rem; margin-bottom: 24px; }

.carousel-wrapper { overflow: hidden; position: relative; }
.carousel { position: relative; }
.carousel-track {
  display: flex;
  gap: 20px;
  transition: transform 0.5s ease;
}

.course-card {
  min-width: 260px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  flex-shrink: 0;
}
.course-card img { width: 100%; height: 150px; object-fit: cover; }
.course-info { padding: 14px; }
.course-tag {
  background: #ede9fe; color: #5b21b6;
  padding: 2px 8px; border-radius: 12px;
  font-size: 0.75rem; font-weight: 600;
}
.course-info h3 { font-size: 0.95rem; margin: 8px 0 4px; }
.course-info p { font-size: 0.8rem; color: #6b7280; }
.course-price { font-size: 1rem; font-weight: 700; color: #4f46e5; }

.carousel-btn {
  position: absolute; top: 50%; transform: translateY(-50%);
  background: rgba(255,255,255,0.9); border: 1px solid #e5e7eb;
  width: 36px; height: 36px; border-radius: 50%;
  font-size: 1.4rem; cursor: pointer; z-index: 10;
}
.prev { left: -18px; }
.next { right: -18px; }
/* NOTE: No pause/stop button element in HTML or CSS */

.instructor-message { padding: 40px; background: #f9fafb; }
.instructor-message h2 { font-size: 1.3rem; margin-bottom: 20px; }
.audio-player { display: flex; flex-direction: column; gap: 8px; }
.audio-description { color: #6b7280; font-size: 0.9rem; }
/* No transcript provided — violation 2 */

.learning-paths { padding: 48px 40px; }
.learning-paths h2 { font-size: 1.5rem; margin-bottom: 28px; }
.paths-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.path-card {
  border: 1px solid #e5e7eb; border-radius: 10px;
  padding: 24px; text-align: center;
}
.path-icon { font-size: 2.5rem; margin-bottom: 12px; }
.path-card h3 { font-size: 1rem; margin-bottom: 8px; }
.path-card p { font-size: 0.85rem; color: #6b7280; margin-bottom: 16px; }
.path-link {
  display: inline-block;
  background: #4f46e5; color: #fff;
  padding: 8px 20px; border-radius: 6px;
  text-decoration: none; font-size: 0.9rem;
  /* VIOLATION 4: No :focus style anywhere in this file since outline:none is global */
}

.edu-footer { background: #1a1a2e; color: #d1d5db; padding: 48px 40px 24px; }
.footer-content { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 40px; margin-bottom: 32px; }
.footer-col h4 { color: #fff; margin-bottom: 14px; font-size: 1rem; }
.footer-col p { font-size: 0.9rem; line-height: 1.6; }
.footer-col a { display: block; color: #9ca3af; text-decoration: none; margin-bottom: 8px; font-size: 0.9rem; }
.footer-bottom { border-top: 1px solid #374151; padding-top: 20px; text-align: center; font-size: 0.85rem; color: #6b7280; }
"""

# ─── Write all site files ─────────────────────────────────────────────────────

files = [
    (1, site1_html, site1_css),
    (2, site2_html, site2_css),
    (3, site3_html, site3_css),
    (4, site4_html, site4_css),
    (5, site5_html, site5_css),
]

for num, html, css in files:
    site_dir = os.path.join(SITES_DIR, f"site_{num}")
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(site_dir, "style.css"), "w", encoding="utf-8") as f:
        f.write(css)
    print(f"  -> site_{num}/index.html and style.css written.")

# ─── ground_truth.json ────────────────────────────────────────────────────────
print("Generating ground_truth.json ...")

ground_truth = {
    "site_1": {
        "total_violations": 5,
        "violations": [
            {
                "wcag_criterion": "1.1.1",
                "element_selector": "img.product-img",
                "severity": "critical",
                "description": "Product images missing alt text — screen readers cannot convey image content to users"
            },
            {
                "wcag_criterion": "1.4.3",
                "element_selector": ".low-contrast-text, .low-contrast-price",
                "severity": "serious",
                "description": "Text color #999999 on white background (#ffffff) provides approximately 2.85:1 contrast ratio, failing the required 4.5:1 minimum for normal text"
            },
            {
                "wcag_criterion": "1.3.1",
                "element_selector": "input[type='email'].email-input",
                "severity": "serious",
                "description": "Email input field has no associated <label> element and no aria-label or aria-labelledby attribute"
            },
            {
                "wcag_criterion": "2.4.4",
                "element_selector": "a.details-link, a.wishlist-link",
                "severity": "moderate",
                "description": "Link text 'click here' is not descriptive out of context — purpose cannot be determined from link text alone"
            },
            {
                "wcag_criterion": "1.4.2",
                "element_selector": "video.promo-video",
                "severity": "critical",
                "description": "Video autoplays with audio and has no controls attribute, preventing users from pausing or stopping the audio"
            }
        ]
    },
    "site_2": {
        "total_violations": 4,
        "violations": [
            {
                "wcag_criterion": "1.3.1",
                "element_selector": "h4.section-heading",
                "severity": "moderate",
                "description": "Heading hierarchy skips levels — page uses h1 then jumps directly to h4, bypassing h2 and h3, breaking document structure"
            },
            {
                "wcag_criterion": "3.1.1",
                "element_selector": "html",
                "severity": "serious",
                "description": "The <html> element is missing the lang attribute; assistive technologies cannot determine the default language of the page"
            },
            {
                "wcag_criterion": "1.4.1",
                "element_selector": ".color-only-error, .breaking-banner",
                "severity": "serious",
                "description": "Color (red) is used as the sole visual indicator for error messages and breaking news urgency — no icon, no text prefix, no pattern"
            },
            {
                "wcag_criterion": "2.1.2",
                "element_selector": "#newsletter-modal",
                "severity": "critical",
                "description": "Modal dialog creates a keyboard trap — focus enters the modal but cannot escape via the Escape key or any keyboard mechanism; no close button is provided"
            }
        ]
    },
    "site_3": {
        "total_violations": 6,
        "violations": [
            {
                "wcag_criterion": "1.3.1",
                "element_selector": "table.fee-table tr:first-child td",
                "severity": "serious",
                "description": "Data table uses <td> elements for column headers instead of <th> elements; screen readers cannot associate data cells with their column or row headers"
            },
            {
                "wcag_criterion": "3.3.2",
                "element_selector": "input#biz-name, input#ein, input#biz-address, input#owner-name, input#owner-email",
                "severity": "moderate",
                "description": "Required form fields have no visual or programmatic indication of being required — no asterisk, no aria-required='true', and no required attribute"
            },
            {
                "wcag_criterion": "3.3.1",
                "element_selector": "span.color-error#email-error",
                "severity": "serious",
                "description": "Error message is identified only through red color styling; no role='alert', no 'Error:' text prefix, and no icon to indicate error status programmatically"
            },
            {
                "wcag_criterion": "4.1.2",
                "element_selector": "div.custom-checkbox",
                "severity": "critical",
                "description": "Custom checkbox widget is implemented as a <div> with no role='checkbox' attribute, no aria-checked state management, and no keyboard Enter/Space event handlers"
            },
            {
                "wcag_criterion": "1.1.1",
                "element_selector": "a.doc-link[href$='.pdf']",
                "severity": "moderate",
                "description": "Link to PDF document does not indicate the file type or file size; users may not be prepared for a file download or format change"
            },
            {
                "wcag_criterion": "2.1.1",
                "element_selector": "div.custom-checkbox",
                "severity": "critical",
                "description": "Custom checkbox is not operable via keyboard — no keydown event listener for Space or Enter keys despite having tabindex='0'"
            }
        ]
    },
    "site_4": {
        "total_violations": 3,
        "violations": [
            {
                "wcag_criterion": "2.2.1",
                "element_selector": "#timeout-overlay",
                "severity": "critical",
                "description": "Session expires after inactivity without any prior accessible warning — no countdown notification, no aria-live announcement, and no option to extend the session before expiry"
            },
            {
                "wcag_criterion": "1.1.1",
                "element_selector": "canvas#health-chart",
                "severity": "serious",
                "description": "Complex blood pressure trend chart rendered on <canvas> has no text alternative, no aria-label with data summary, no associated data table, and no role='img' with description"
            },
            {
                "wcag_criterion": "2.5.8",
                "element_selector": "button.tiny-btn",
                "severity": "moderate",
                "description": "Reschedule and Cancel appointment buttons have a CSS size of 18×18 pixels, below the WCAG 2.2 minimum target size of 24×24 CSS pixels"
            }
        ]
    },
    "site_5": {
        "total_violations": 5,
        "violations": [
            {
                "wcag_criterion": "2.3.1",
                "element_selector": "div.flash-banner",
                "severity": "critical",
                "description": "Flash sale banner uses a CSS animation (flashSale) cycling at 0.2 seconds per iteration — equivalent to 5 Hz, exceeding the 3 flashes per second threshold and posing seizure risk"
            },
            {
                "wcag_criterion": "1.2.1",
                "element_selector": "audio[src='instructor-welcome.mp3']",
                "severity": "serious",
                "description": "Audio-only content (instructor welcome message) is provided without a text transcript; deaf and hard-of-hearing users have no access to the audio content"
            },
            {
                "wcag_criterion": "1.4.5",
                "element_selector": "img.hero-heading-img",
                "severity": "moderate",
                "description": "The main page heading is presented as an image of text (hero-heading.png) with alt='' making it invisible to screen readers; real HTML text with styling should be used instead"
            },
            {
                "wcag_criterion": "2.4.7",
                "element_selector": "*",
                "severity": "critical",
                "description": "Global CSS rule '* { outline: none; }' removes the visible focus indicator from all interactive elements — keyboard users cannot determine which element currently has focus"
            },
            {
                "wcag_criterion": "2.2.2",
                "element_selector": "#course-carousel",
                "severity": "serious",
                "description": "Auto-advancing course carousel moves every 2 seconds with no pause, stop, or hide mechanism — users with cognitive disabilities or motion sensitivity cannot stop the movement"
            }
        ]
    }
}

with open(os.path.join(BASE_DIR, "ground_truth.json"), "w", encoding="utf-8") as f:
    json.dump(ground_truth, f, indent=2)
print("  -> ground_truth.json written.")

# ─── README.md ────────────────────────────────────────────────────────────────
readme = """# IT-P4: AccessibilityAI — Test Websites Dataset

## Overview
Five test websites with deliberately embedded WCAG 2.2 violations for evaluating
automated accessibility analysis tools and AI-powered auditing systems.

## Directory Structure
```
IT-P4/
├── test_websites/
│   ├── site_1/          # E-commerce product page
│   │   ├── index.html
│   │   └── style.css
│   ├── site_2/          # News article page
│   ├── site_3/          # Government form page
│   ├── site_4/          # Healthcare portal
│   └── site_5/          # Education platform
├── ground_truth.json    # Known violations per site
└── README.md
```

## Sites Summary

| Site | Type | WCAG Violations | Key Issues |
|------|------|-----------------|------------|
| site_1 | E-commerce product page | 5 | Missing alt text, low contrast, unlabeled input, non-descriptive links, autoplay video |
| site_2 | News article | 4 | Skipped headings, missing lang, color-only errors, keyboard trap |
| site_3 | Government form | 6 | Table no headers, unmarked required fields, color-only errors, ARIA-less custom control, PDF no type label |
| site_4 | Healthcare portal | 3 | Session timeout no warning, chart no text alt, small click targets |
| site_5 | Education platform | 5 | Flashing content (>3 Hz), audio no transcript, image of text heading, no focus indicator, carousel no pause |

## WCAG Criteria Tested

| Criterion | Description | Sites |
|-----------|-------------|-------|
| 1.1.1 | Non-text Content | 1, 3, 4 |
| 1.2.1 | Audio-only Content | 5 |
| 1.3.1 | Info and Relationships | 1, 2, 3 |
| 1.4.1 | Use of Color | 2, 3 |
| 1.4.2 | Audio Control | 1 |
| 1.4.3 | Contrast (Minimum) | 1 |
| 1.4.5 | Images of Text | 5 |
| 2.1.1 | Keyboard | 3 |
| 2.1.2 | No Keyboard Trap | 2 |
| 2.2.1 | Timing Adjustable | 4 |
| 2.2.2 | Pause, Stop, Hide | 5 |
| 2.3.1 | Three Flashes | 5 |
| 2.4.4 | Link Purpose | 1 |
| 2.4.7 | Focus Visible | 5 |
| 3.1.1 | Language of Page | 2 |
| 3.3.1 | Error Identification | 3 |
| 3.3.2 | Labels or Instructions | 3 |
| 4.1.2 | Name, Role, Value | 3 |
| 2.5.8 | Target Size (Minimum) | 4 |

## Ground Truth Format
`ground_truth.json` contains per-site violation details:
```json
{
  "site_N": {
    "total_violations": <int>,
    "violations": [
      {
        "wcag_criterion": "<N.N.N>",
        "element_selector": "<CSS selector>",
        "severity": "critical|serious|moderate|minor",
        "description": "<detailed description>"
      }
    ]
  }
}
```

## Severity Levels
- **critical** — Completely blocks access for affected users
- **serious** — Significantly impairs access
- **moderate** — Creates barriers but workarounds exist
- **minor** — Best-practice issue with minimal impact
"""

with open(os.path.join(BASE_DIR, "README.md"), "w", encoding="utf-8") as f:
    f.write(readme)
print("  -> README.md written.")
print("\nIT-P4 generation complete.")
"""
