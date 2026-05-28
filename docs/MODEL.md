# Data Model

## The Core Idea

Two tables do the real work: `RawIngestion` stores exactly what came in from
the client, untouched. `NormalizedEmission` stores what we calculated from it.
They are linked by a foreign key. If our normalizer had a bug, we can reprocess
from the raw without asking the client to re-upload.

---

## Schema

```
Tenant
  └── User
  └── RawIngestion
        └── NormalizedEmission
              └── EmissionAuditLog
```

### Tenant
Breathe ESG is multi-client. Every data table has a `tenant` FK and every API
view filters by `request.user.tenant` before returning anything. Simple and
enforced at the application layer.

### User
Extends Django's AbstractUser with two fields: `tenant` (which client they
belong to) and `role` (analyst or admin). Session authentication, no tokens.

### RawIngestion
One row per uploaded file.

```
id                  UUID
tenant              FK → Tenant
source_type         SAP | UTILITY | TRAVEL
original_filename   string
uploaded_by         FK → User
uploaded_at         datetime
raw_content         JSON  ← full file content stored here
status              processing | completed | failed | partial
row_count_total     int
row_count_success   int
row_count_failed    int
error_log           JSON  ← per-row error descriptions
```

`raw_content` is the source of truth. `status = partial` means some rows
parsed and some did not, which is the normal case for messy real-world files.

### NormalizedEmission
One row per data point, regardless of source.

```
id                      UUID
tenant                  FK → Tenant
raw_ingestion           FK → RawIngestion
source_type             SAP | UTILITY | TRAVEL
source_row_reference    string  ← "row_12" or "SEG-007"

scope                   1 | 2 | 3
category                string
activity_description    text

period_start            date
period_end              date

quantity_original       decimal  ← what the source said
unit_original           string
quantity_normalized     decimal  ← after unit conversion
unit_normalized         string
conversion_applied      text     ← "1 kg diesel = 1.163 litres"

emission_factor_used    decimal
emission_factor_unit    string
emission_factor_source  string
co2e_kg                 decimal, nullable

confidence_score        float 0.0–1.0
flags                   JSON array of warning strings

review_status           pending | approved | rejected | locked
reviewed_by             FK → User
reviewed_at             datetime
review_note             text
locked_at               datetime
locked_by               FK → User

metadata                JSON  ← source-specific fields that dont fit
created_at              datetime
updated_at              datetime
```

**Why nullable co2e_kg:** A flight where the airport code is missing from our
lookup cannot be calculated. We store the row anyway at confidence 0.0 and flag
it. Dropping it would silently undercount emissions, which is worse.

**Why metadata as JSON:** SAP rows need kostenstelle and werk. Travel rows need
employee_id and trip_id. Rather than polluting the shared schema with
source-specific columns, we store them in a flexible JSON field.

### EmissionAuditLog
Append-only. Never updated or deleted.

```
id              UUID
emission        FK → NormalizedEmission
action          created | edited | approved | rejected | locked
performed_by    FK → User
performed_at    datetime
previous_value  JSON
new_value       JSON
note            text
```

Every state change writes a row here. If an analyst changes an emission factor
before approving, the before and after values are both stored.

---

## Scope Assignment

| Source | Scope | Why |
|--------|-------|-----|
| SAP fuels | 1 | Direct combustion in company-owned assets |
| Utility electricity | 2 | Purchased electricity |
| Travel (all segments) | 3 | Value chain, employee business travel |

Assigned by the parser at ingestion time. Stored explicitly so queries like
`filter(scope=1)` need no joins.

## Unit Normalization

Each fuel type normalizes to whatever unit the DEFRA emission factor expects.

| Input | Normalize to | Reason |
|-------|-------------|--------|
| Diesel (any unit) | Litres | DEFRA factor is per litre |
| Natural gas (any unit) | kWh | DEFRA factor is per kWh |
| Electricity | kWh | Already in correct unit |
| Flights | km | DEFRA factor is per passenger km |
| Hotels | nights | DEFRA factor is per room night |
| Ground transport | km | DEFRA factor is per km |

Original quantity and unit are always preserved. We never overwrite them.

## Confidence Score

Starts at 1.0. Each parser deducts for problems it finds.

| Problem | Deduction |
|---------|-----------|
| Volume 10x above cost center average | −0.5 |
| Unknown unit | −0.3 |
| Distance estimated via default | −0.4 |
| Unknown ground transport type | −0.2 |
| Unknown cost center or grid region | −0.1 |
| Distance calculated via haversine | −0.05 |
| Airport not in lookup table | set to 0.0 |

Confidence is a signal for the analyst, not a hard gate. A row with score 0.3
can still be approved after manual verification.