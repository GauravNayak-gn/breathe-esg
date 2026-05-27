import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime

COST_CENTER_LOOKUP = {
    '1000': {
        'location': 'Frankfurt Manufacturing Plant',
        'country': 'DE',
        'city': 'Frankfurt'
    },
    '2300': {
        'location': 'London Head Office',
        'country': 'GB',
        'city': 'London'
    },
    '3100': {
        'location': 'Hamburg Logistics Centre',
        'country': 'DE',
        'city': 'Hamburg'
    },
    '4000': {
        'location': 'Chicago Distribution Hub',
        'country': 'US',
        'city': 'Chicago'
    },
}

MATERIAL_LOOKUP = {
    'DIESEL-B7': {
        'fuel_type': 'diesel',
        'scope': 1,
        'category': 'Mobile combustion'
    },
    'ERDGAS': {
        'fuel_type': 'natural_gas',
        'scope': 1,
        'category': 'Stationary combustion'
    },
    'HEIZOEL': {
        'fuel_type': 'heating_oil',
        'scope': 1,
        'category': 'Stationary combustion'
    },
    'UNLEADED-95': {
        'fuel_type': 'petrol',
        'scope': 1,
        'category': 'Mobile combustion'
    },
}


def parse_german_decimal(value_str):
    """
    SAP German locale uses comma as decimal separator.
    Some rows may use period if plant locale differs.
    Returns Decimal or None.
    """
    if not value_str or not value_str.strip():
        return None
    v = value_str.strip()
    # If both separators present, German format: 1.234,56
    if ',' in v and '.' in v:
        v = v.replace('.', '').replace(',', '.')
    elif ',' in v:
        # Only comma: treat as decimal separator
        v = v.replace(',', '.')
    # else period only: standard format, use as is
    try:
        return Decimal(v)
    except InvalidOperation:
        return None


def parse_sap_date(date_str):
    """
    SAP German locale exports dates as DD.MM.YYYY
    """
    if not date_str or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), '%d.%m.%Y').date()
    except ValueError:
        return None


def parse_sap_file(file_content, raw_ingestion_id, tenant_id):
    """
    Parse SAP flat file CSV export.
    Returns (successes, errors).
    successes: list of dicts for NormalizedEmission creation
    errors: list of dicts describing row-level failures
    """
    from emissions.emission_factors import (
        DIESEL_KG_CO2E_PER_LITRE,
        PETROL_KG_CO2E_PER_LITRE,
        HEATING_OIL_KG_CO2E_PER_LITRE,
        NATURAL_GAS_KG_CO2E_PER_KWH,
        DIESEL_LITRES_PER_KG,
        NATURAL_GAS_KWH_PER_KG,
        NATURAL_GAS_KWH_PER_M3,
        LITRES_PER_US_GALLON,
    )

    successes = []
    errors = []

    reader = csv.DictReader(io.StringIO(file_content), delimiter=';')

    # Track quantities per cost center for anomaly detection
    cost_center_quantities = {}

    rows = list(reader)

    # First pass: collect averages for anomaly detection
    for row in rows:
        kst = (row.get('Kostenstelle') or '').strip()
        qty = parse_german_decimal(row.get('Menge', ''))
        if kst and qty is not None:
            cost_center_quantities.setdefault(kst, [])
            cost_center_quantities[kst].append(float(qty))

    averages = {
        kst: sum(vals) / len(vals)
        for kst, vals in cost_center_quantities.items()
    }

    for row_num, row in enumerate(rows, start=2):
        try:
            result = _process_sap_row(
                row, row_num, raw_ingestion_id, tenant_id,
                averages,
            )
            if result['success']:
                successes.append(result['data'])
            else:
                errors.append(result['error'])
        except Exception as e:
            errors.append({
                'row': row_num,
                'error': f'Unexpected error: {str(e)}',
                'raw': dict(row)
            })

    return successes, errors


def _process_sap_row(row, row_num, raw_ingestion_id, tenant_id, averages):
    from emissions.emission_factors import (
        DIESEL_KG_CO2E_PER_LITRE,
        PETROL_KG_CO2E_PER_LITRE,
        HEATING_OIL_KG_CO2E_PER_LITRE,
        NATURAL_GAS_KG_CO2E_PER_KWH,
        DIESEL_LITRES_PER_KG,
        NATURAL_GAS_KWH_PER_KG,
        NATURAL_GAS_KWH_PER_M3,
        LITRES_PER_US_GALLON,
    )

    flags = []
    confidence = 1.0

    # Parse date - use Buchungsdatum (posting date) as period
    posting_date = parse_sap_date(row.get('Buchungsdatum', ''))
    if posting_date is None:
        return {
            'success': False,
            'error': {
                'row': row_num,
                'error': f"Invalid or missing Buchungsdatum: {row.get('Buchungsdatum')}",
                'raw': dict(row)
            }
        }

    # Parse quantity
    quantity = parse_german_decimal(row.get('Menge', ''))
    if quantity is None:
        return {
            'success': False,
            'error': {
                'row': row_num,
                'error': 'Missing or unparseable Menge (quantity)',
                'raw': dict(row)
            }
        }

    unit = (row.get('Mengeneinheit') or '').strip().upper()
    material = (row.get('Material') or '').strip().upper()
    kostenstelle = (row.get('Kostenstelle') or '').strip()
    werk = (row.get('Werk') or '').strip()
    material_desc = (row.get('Materialbezeichnung') or '').strip()

    # Resolve material
    material_info = MATERIAL_LOOKUP.get(material)
    if material_info is None:
        return {
            'success': False,
            'error': {
                'row': row_num,
                'error': f'Unknown material code: {material}',
                'raw': dict(row)
            }
        }

    fuel_type = material_info['fuel_type']
    scope = material_info['scope']
    category = material_info['category']

    # Resolve cost center
    cc_info = COST_CENTER_LOOKUP.get(kostenstelle, {})
    location_str = cc_info.get('location', f'Cost Center {kostenstelle}')
    if not cc_info:
        flags.append(f'Unknown cost center: {kostenstelle}')
        confidence -= 0.1

    # Anomaly detection
    avg = averages.get(kostenstelle)
    if avg and avg > 0:
        ratio = float(quantity) / avg
        if ratio > 10:
            flags.append(
                f'Volume is {ratio:.0f}x the average for cost center {kostenstelle}'
            )
            confidence -= 0.5

    # Unit normalization and emission calculation
    quantity_normalized = None
    unit_normalized = ''
    conversion_applied = ''
    emission_factor = None
    emission_factor_unit = ''
    co2e_kg = None

    if fuel_type == 'diesel':
        # Convert everything to litres
        if unit == 'L':
            quantity_normalized = quantity
            unit_normalized = 'litres'
            conversion_applied = 'No conversion needed'
        elif unit == 'KG':
            quantity_normalized = quantity * Decimal(str(DIESEL_LITRES_PER_KG))
            unit_normalized = 'litres'
            conversion_applied = f'1 kg diesel = {DIESEL_LITRES_PER_KG} litres'
        elif unit == 'GAL':
            quantity_normalized = quantity * Decimal(str(LITRES_PER_US_GALLON))
            unit_normalized = 'litres'
            conversion_applied = f'1 US gallon = {LITRES_PER_US_GALLON} litres'
        else:
            flags.append(f'Unrecognised unit for diesel: {unit}')
            confidence -= 0.3

        if quantity_normalized is not None:
            emission_factor = Decimal(str(DIESEL_KG_CO2E_PER_LITRE))
            emission_factor_unit = 'kg CO2e per litre'
            co2e_kg = quantity_normalized * emission_factor

    elif fuel_type == 'petrol':
        if unit == 'L':
            quantity_normalized = quantity
            unit_normalized = 'litres'
            conversion_applied = 'No conversion needed'
        elif unit == 'GAL':
            quantity_normalized = quantity * Decimal(str(LITRES_PER_US_GALLON))
            unit_normalized = 'litres'
            conversion_applied = f'1 US gallon = {LITRES_PER_US_GALLON} litres'
        else:
            flags.append(f'Unrecognised unit for petrol: {unit}')
            confidence -= 0.3

        if quantity_normalized is not None:
            emission_factor = Decimal(str(PETROL_KG_CO2E_PER_LITRE))
            emission_factor_unit = 'kg CO2e per litre'
            co2e_kg = quantity_normalized * emission_factor

    elif fuel_type == 'natural_gas':
        # Convert everything to kWh
        if unit == 'KWH':
            quantity_normalized = quantity
            unit_normalized = 'kWh'
            conversion_applied = 'No conversion needed'
        elif unit == 'KG':
            quantity_normalized = quantity * Decimal(str(NATURAL_GAS_KWH_PER_KG))
            unit_normalized = 'kWh'
            conversion_applied = f'1 kg natural gas = {NATURAL_GAS_KWH_PER_KG} kWh'
        elif unit == 'M3':
            quantity_normalized = quantity * Decimal(str(NATURAL_GAS_KWH_PER_M3))
            unit_normalized = 'kWh'
            conversion_applied = f'1 m3 natural gas = {NATURAL_GAS_KWH_PER_M3} kWh'
        else:
            flags.append(f'Unrecognised unit for natural gas: {unit}')
            confidence -= 0.3

        if quantity_normalized is not None:
            emission_factor = Decimal(str(NATURAL_GAS_KG_CO2E_PER_KWH))
            emission_factor_unit = 'kg CO2e per kWh'
            co2e_kg = quantity_normalized * emission_factor

    elif fuel_type == 'heating_oil':
        if unit == 'L':
            quantity_normalized = quantity
            unit_normalized = 'litres'
            conversion_applied = 'No conversion needed'
        else:
            flags.append(f'Unrecognised unit for heating oil: {unit}')
            confidence -= 0.3

        if quantity_normalized is not None:
            emission_factor = Decimal(str(HEATING_OIL_KG_CO2E_PER_LITRE))
            emission_factor_unit = 'kg CO2e per litre'
            co2e_kg = quantity_normalized * emission_factor

    activity_description = f'{material_desc} - {location_str} ({werk})'

    return {
        'success': True,
        'data': {
            'tenant_id': tenant_id,
            'raw_ingestion_id': raw_ingestion_id,
            'source_type': 'SAP',
            'source_row_reference': f'row_{row_num}',
            'scope': scope,
            'category': category,
            'activity_description': activity_description,
            'period_start': posting_date,
            'period_end': posting_date,
            'quantity_original': quantity,
            'unit_original': unit,
            'quantity_normalized': quantity_normalized,
            'unit_normalized': unit_normalized,
            'conversion_applied': conversion_applied,
            'emission_factor_used': emission_factor,
            'emission_factor_unit': emission_factor_unit,
            'emission_factor_source': 'DEFRA 2023',
            'co2e_kg': co2e_kg,
            'confidence_score': max(0.0, confidence),
            'flags': flags,
            'review_status': 'pending',
            'metadata': {
                'kostenstelle': kostenstelle,
                'werk': werk,
                'material_code': material,
                'belegdatum': str(row.get('Belegdatum', '')),
            }
        }
    }