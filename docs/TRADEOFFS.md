# Tradeoffs

---

## 1. No Duplicate Detection

If the same file is uploaded twice, we create duplicate emission rows. Fixing
this properly requires a deduplication key for each source type, and defining
that key is genuinely hard.

For SAP: the natural key is (cost center, plant, material, date, quantity).
But what if SAP was corrected after the first export? Same natural key,
different quantity. Is that a duplicate or an amendment?

For travel: segment IDs are platform-specific and not guaranteed stable between
exports. Booking reference is shared between outbound and return legs.

The short-term workaround is manual: if a duplicate upload happens, the analyst
rejects the duplicate rows. The audit log preserves the history. This is
acceptable for a prototype with a small dataset. At scale, the right answer is
content hashing the raw file and rejecting re-uploads of identical files.

---

## 2. No Automatic Period Proration for Utility Bills

When a billing cycle does not align with a calendar month, the correct thing to
do depends on information we do not have: the actual consumption profile within
the billing period. Uniform proration (allocate proportionally by days) is
mathematically simple but wrong for any site with non-uniform usage, which is
most sites.

We flag the misalignment and leave the allocation decision to the analyst. This
looks like a missing feature but it is actually the more honest choice. A
number that looks precise but embeds an unknown error is more dangerous than a
flag that prompts a human to make an informed decision.

The real fix is half-hourly interval data, which gives exact period allocation.
The schema supports it: period_start and period_end can represent any interval.

---

## 3. No Market-Based Scope 2

The GHG Protocol allows two Scope 2 accounting methods. Location-based uses the
regional grid intensity factor. Market-based uses the emission factor of the
specific electricity instrument the company purchased, such as a renewable
energy certificate (REGO in the UK).

We implement location-based only. Market-based requires knowing which
certificates the client holds, their vintage, and the residual mix factor for
any uncovered consumption. This information is not in a standard utility portal
export. It lives in procurement records and certificate registries.

For a client that has purchased REGOs for all their consumption, market-based
Scope 2 would be near zero and location-based would show tens of thousands of
kg CO2e. The difference is material and the client will eventually ask for it.

The right answer is a separate data input for energy attribute certificates
linked to specific meters and periods. That is a future feature with a clear
data model extension point.