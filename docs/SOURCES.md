# Sources

---

## SAP Fuel and Procurement

### What Was Researched
SAP Help Portal documentation for MB52 (warehouse stocks report) and MIGO
(goods movement). Stack Overflow threads on parsing SAP flat file exports.
GitHub repositories with SAP CSV test data. SAP's ALV Grid export behavior
in German versus English locale configurations.

### What Was Learned
SAP's ALV Grid is the standard report display framework. Its export produces
semicolon-delimited files when running in German locale because the comma is
reserved as the decimal separator. Column headers reflect the system language:
a German SAP instance produces Buchungsdatum, Menge, Mengeneinheit. The same
system in English produces PostingDate, Quantity, UnitOfMeasure.

Date format is locale-dependent: DD.MM.YYYY in German, MM/DD/YYYY in US.
Decimal separator is locale-dependent: comma in German, period in US. Both
can appear in the same file when different users have different locale settings
in their SAP profile, which is a real problem with no clean solution.

Movement type 201 is a goods issue to a cost center, the correct movement type
for fuel drawn from a company tank for operational use.

### What The Sample Data Looks Like and Why
The file uses semicolons and German headers because the fictional client is a
German-headquartered company. Row 1 has a comma decimal (450,50) and row 3 has
a period decimal (89.3): this inconsistency tests that our parser handles both
without assuming one locale throughout the file. Row 11 has an empty Menge
field, which happens in real SAP exports when a posting is made without a
quantity (a known SAP data quality issue). Row 12 has 15,000 KG of diesel,
which is statistically anomalous and triggers the flag logic.

### What Would Break in Production
Any material code not in our four-entry lookup table produces a parse error.
A real client has hundreds of material codes. Character encoding is a genuine
problem: SAP can export Windows-1252 or UTF-8 and the Heizöl umlaut will
corrupt silently if we assume the wrong encoding. If the client's IT team
changes the SAP system language, every column header changes and the parser
breaks immediately.

---

## Utility Electricity Data

### What Was Researched
Green Button Alliance specification (greenbuttonalliance.org). Octopus Energy
developer API documentation. National Grid ESO Carbon Intensity API and their
regional intensity methodology. Ofgem documentation on HH vs NHH metering and
UK electricity settlement periods. BEIS 2023 electricity generation mix data.

### What Was Learned
UK commercial electricity contracts frequently start billing from the contract
or meter installation date, not the first of the month. This means billing
period misalignment is the norm, not the exception.

Half-hourly meters (mandatory above 100 kW peak demand) record consumption in
every 30-minute settlement period. Non-half-hourly meters record cumulative
consumption between actual reads, which may be months apart with estimated
reads in between.

Regional carbon intensity varies significantly across the UK. Scotland at
0.176 kg CO2e/kWh versus London at 0.231 reflects the difference between
hydro and wind generation in Scotland and a more fossil-fuel-dependent mix in
southern England. Using a national average for a Scottish facility overstates
Scope 2 emissions by roughly 15%.

### What The Sample Data Looks Like and Why
Two accounts bill on calendar months (Bristol). One bills on a mid-month cycle
(London, 17th to 16th) to test the misalignment flag. The Edinburgh retail
unit has no peak demand field because it is an NHH meter. Consumption varies
realistically month to month rather than being flat, because flat consumption
at an industrial site would itself be suspicious.

### What Would Break in Production
Every utility portal uses different column names. Our parser assumes exact
header strings from our sample. A real deployment needs a configurable column
mapping per provider. Some utilities export MWh rather than kWh: a file mixing
units would produce values off by a factor of 1000 for the MWh rows. Negative
consumption rows (billing corrections from estimated-to-actual read adjustments)
would produce negative CO2e and should be treated as period adjustments, not
standard consumption rows.

---

## Corporate Travel Data

### What Was Researched
SAP Concur developer portal: Itinerary API v1, Extract API batch file format.
Navan API documentation. DEFRA 2023 conversion factors: business travel
section covering flights by cabin class and haul type, hotels, ground
transport. OurAirports database for airport coordinates. ICAO Carbon Emissions
Calculator methodology and its differences from DEFRA.

### What Was Learned
The Concur Itinerary API returns trips as parent objects with nested booking
segments. Distance is not guaranteed to be present: bookings made through
GDS systems (Amadeus, Sabre) often do not include distance in the booking
record. Null distance_km is normal, not an edge case.

DEFRA 2023 flight factors differ significantly by cabin class because they use
a seat area allocation method. A business class seat occupies roughly three
times the floor space of an economy seat, so business class carries roughly
three times the per-passenger emission allocation. Business long haul is
0.57255 kg CO2e per passenger km versus economy long haul at 0.19085.

DEFRA includes radiative forcing in their flight factors. At cruise altitude,
contrail formation and NOx effects increase the warming impact beyond the CO2
alone. ICAO's calculator does not include radiative forcing. We follow DEFRA
because our client is UK-based and this is the UK government standard.

DEFRA classifies flights as domestic (under 463 km), short haul, and long haul.
We simplify to two categories because we do not have a separate domestic factor
and the difference between domestic and short haul is small.

### What The Sample Data Looks Like and Why
Trip 1 (LHR-JFK, business class) has null distances to test haversine
calculation on a long haul route. Trip 2 (LHR-SIN, economy) is ultra-long haul
and tests that the correct long haul economy factor is applied. It also
includes a train segment with a known distance of 18 km, contrasting with taxi
segments elsewhere that have null distances. Trip 3 (LHR-CDG, economy) is
short haul with distance provided, testing the non-null distance path. At
344 km it is technically domestic under DEFRA's three-way classification, which
is a documented simplification. Trip 4 (LHR-DXB, first class) uses the highest
emission factor and shares an employee ID with trip 1 to test per-employee
aggregation.

### What Would Break in Production
Our airport coordinate lookup has 10 airports. Any flight involving an airport
not in the table produces a null co2e_kg. A real deployment needs the full
OurAirports dataset loaded into the database. Cabin class strings vary by
platform: Concur may return "C" (the GDS booking class code) instead of
"business". Rail segments in Concur are a distinct type from ground transport.
Eurostar has an emission factor of approximately 0.006 kg CO2e per passenger km
(nuclear-powered electricity) versus our taxi default of 0.149. Misclassifying
a London-Paris Eurostar as a taxi would overstate emissions by roughly 25x.