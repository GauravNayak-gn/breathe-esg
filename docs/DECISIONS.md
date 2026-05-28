# Decisions

---

## SAP: Flat File Over IDoc or OData

IDoc requires an ABAP developer to configure message types. OData requires the
client's IT team to activate services and whitelist our IP. Neither happens
during onboarding week.

A flat file is what a sustainability manager actually produces: open SAP, run
the MB52 material consumption report, click export. That is what we handle.

**Subset handled:** Goods movement type 201 (goods issue to cost center) for
four fuel materials: DIESEL-B7, ERDGAS, HEIZOEL, UNLEADED-95. German locale
dates and decimals. Units L, KG, GAL, M3.

**Ignored:** Procurement data, refrigerants, fleet data from SAP PM, any
material code not in our lookup table.

**Would ask the PM:** Is this a one-time export or does the client expect a
recurring automated extract? If recurring, we should negotiate OData access
with their IT team rather than relying on manual downloads.

---

## Utility: Portal CSV Over PDF or API

PDF parsing requires templated extraction rules per utility provider. Every
provider formats their bill differently. The error rate on an untested parser
would create more data quality problems than it solves.

Direct API access exists for some utilities (Octopus has a good public API)
but most UK commercial providers do not offer self-service API access for
billing data.

Portal CSV is what a UK facilities manager actually does. It is structured and
requires no IT involvement.

**Subset handled:** Consumption in kWh, billing period dates, grid region, HH
and NHH meter types, UK regions only.

**Ignored:** PDF bills, MWh inputs, time-of-use tariff breakdowns, market-based
Scope 2 (which requires knowing the specific renewable certificate purchased).

**Would ask the PM:** Which utility providers does this client use? Octopus
would let us automate the pull entirely. Most others would not.

---

## Billing Period Misalignment: Flag, Do Not Prorate

When a billing cycle runs January 17 to February 16, automatic proration would
split the consumption 15/31 to January and 16/28 to February. But proration
assumes uniform daily consumption, which is wrong for most industrial sites.
A manufacturing plant running a production campaign in week one of February
has a consumption profile that proration would misrepresent systematically.

We store the raw billing dates and flag the misalignment. The analyst decides
how to handle it because the analyst knows the site.

**Would ask the PM:** Does the client have half-hourly interval data? With HH
data we can aggregate to any period boundary exactly and there is no problem.

---

## Travel: JSON Upload Over Concur API

Calling the Concur API directly requires OAuth credentials from the client's
Concur instance, which we do not have during onboarding. A JSON export from
the Concur or Navan admin panel is realistic and preserves the nested trip
structure (one trip, multiple segments) that a flat CSV export loses.

**Subset handled:** Flight, hotel, and ground segments. Cabin classes economy,
premium economy, business, first. Haversine distance when not provided.
Short haul under 3700 km, long haul over.

**Ignored:** Rail as a distinct segment type, car rental, multi-passenger
bookings, connecting flights that appear as a single booking record.

**Would ask the PM:** Can the client grant Concur API credentials? That removes
the manual export step and lets us pull on a schedule.

---

## Missing Flight Distance: Haversine Over Null

When distance_km is null, we calculate great circle distance from airport
coordinates using the haversine formula. This is the same method DEFRA and
ICAO use in their own calculators. It is reproducible and auditable.

The alternative is leaving co2e_kg null. That silently undercounts emissions,
which is worse than a documented approximation.

We flag the row and deduct 0.05 from confidence. The analyst can override.

---

## Missing Ground Transport Distance: Default 25 km

For taxis with no distance, we apply a 25 km default and deduct 0.4 from
confidence. 25 km approximates a typical airport-to-city-centre journey across
our sample cities. The flag is explicit and the confidence hit is large enough
that the analyst will notice.

**Would ask the PM:** Can we require the travel platform to capture distance
for all ground segments going forward? Estimating it is the worst option.

---

## Emission Factors: DEFRA 2023 Throughout

DEFRA is the UK government standard, updated annually, freely available, and
accepted by UK auditors. Our sample client is UK-based.

Known inaccuracy: the Chicago cost center (US01) should use EPA factors for
Scope 1. We use DEFRA for simplicity and document it here.

**Would ask the PM:** What reporting framework is the client using? CDP and
GRI accept DEFRA. Some frameworks mandate GHG Protocol factors specifically.

---

## Reject Requires a Note

An analyst can approve with no comment. Rejection requires a note explaining
why. This is deliberate: rejections create a gap in the reported data and
auditors will ask why. The note becomes part of the audit trail.