# All factors sourced from DEFRA 2023 Greenhouse Gas Conversion Factors
# https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting

# Scope 1 - kg CO2e per litre
DIESEL_KG_CO2E_PER_LITRE = 2.51
PETROL_KG_CO2E_PER_LITRE = 2.31
HEATING_OIL_KG_CO2E_PER_LITRE = 2.54

# Natural gas - kg CO2e per kWh
NATURAL_GAS_KG_CO2E_PER_KWH = 0.18254

# Unit conversions for fuels
# 1 kg diesel = 1.163 litres (density approximately 0.86 kg/L)
DIESEL_LITRES_PER_KG = 1.163
# 1 kg natural gas = 13.1 kWh (calorific value)
NATURAL_GAS_KWH_PER_KG = 13.1
# 1 m3 natural gas = 10.55 kWh
NATURAL_GAS_KWH_PER_M3 = 10.55
# 1 US gallon = 3.785 litres
LITRES_PER_US_GALLON = 3.785

# Scope 2 - kg CO2e per kWh
# UK grid by region, source: National Grid ESO / BEIS 2023
ELECTRICITY_BY_REGION = {
    'London': 0.231,
    'South West': 0.198,
    'North West': 0.209,
    'Scotland': 0.176,
    'default': 0.20785,  # UK national average
}

# Scope 3 - flights
# kg CO2e per passenger km, includes radiative forcing
# Short haul = under 3700 km, Long haul = over 3700 km
FLIGHT_FACTORS = {
    ('economy', 'short'): 0.15553,
    ('economy', 'long'): 0.19085,
    ('business', 'short'): 0.23329,
    ('business', 'long'): 0.57255,
    ('first', 'long'): 0.76340,
    ('first', 'short'): 0.23329,  # Use business rate for first short haul
    ('premium_economy', 'short'): 0.18671,
    ('premium_economy', 'long'): 0.28989,
}

SHORT_HAUL_MAX_KM = 3700

# Scope 3 - hotels
# kg CO2e per room night
HOTEL_NIGHT_UK = 20.8
HOTEL_NIGHT_INTERNATIONAL = 31.0

# Scope 3 - ground transport
# kg CO2e per km
GROUND_TRANSPORT = {
    'taxi': 0.14869,
    'car': 0.16844,
    'train': 0.03549,
    'bus': 0.10312,
}

# Average urban taxi journey km - used when distance is null
# Assumption: average airport taxi is 25 km
# Documented assumption, flagged for analyst review
TAXI_DEFAULT_KM = 25