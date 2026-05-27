import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime


def parse_utility_date(date_str):
    """
    Portal exports use DD/MM/YYYY
    """
    if not date_str or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), '%d/%m/%Y').date()
    except ValueError:
        return None


def parse_decimal(value_str):
    if not value_str or not value_str.strip():
        return None
    try:
        return Decimal(value_str.strip())
    except InvalidOperation:
        return None


def parse_utility_file(file_content, raw_ingestion_id, tenant_id):
    """
    Parse utility portal CSV export.
    Returns (successes, errors).
    """
    from emissions.emission_factors import ELECTRICITY_BY_REGION

    successes = []
    errors = []

    reader = csv.DictReader(io.StringIO(file_content))

    for row_num, row in enumerate(reader, start=2):
        try:
            result = _process_utility_row(
                row, row_num, raw_ingestion_id, tenant_id
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


def _process_utility_row(row, row_num, raw_ingestion_id, tenant_id):
    from emissions.emission_factors import ELECTRICITY_BY_REGION

    flags = []
    confidence = 1.0

    period_start = parse_utility_date(row.get('Billing Period Start', ''))
    period_end = parse_utility_date(row.get('Billing Period End', ''))

    if period_start is None or period_end is None:
        return {
            'success': False,
            'error': {
                'row': row_num,
                'error': 'Invalid billing period dates',
                'raw': dict(row)
            }
        }

    consumption_kwh = parse_decimal(row.get('Consumption (kWh)', ''))
    if consumption_kwh is None:
        return {
            'success': False,
            'error': {
                'row': row_num,
                'error': 'Missing consumption kWh',
                'raw': dict(row)
            }
        }

    grid_region = (row.get('Grid Region') or '').strip()
    meter_id = (row.get('Meter ID') or '').strip()
    account_number = (row.get('Account Number') or '').strip()
    address = (row.get('Service Address') or '').strip()
    tariff = (row.get('Tariff Code') or '').strip()
    meter_type = (row.get('Meter Type') or '').strip()

    # Check if billing period crosses month boundary
    if period_start.month != period_end.month:
        flags.append(
            f'Billing period crosses month boundary: '
            f'{period_start} to {period_end}. '
            f'Pro-rating not applied. Analyst should verify period allocation.'
        )
        confidence -= 0.1

    # Get emission factor for this region
    emission_factor = ELECTRICITY_BY_REGION.get(
        grid_region,
        ELECTRICITY_BY_REGION['default']
    )
    if grid_region not in ELECTRICITY_BY_REGION:
        flags.append(
            f'Unknown grid region: {grid_region}. '
            f'Using UK national average emission factor.'
        )
        confidence -= 0.1

    emission_factor_decimal = Decimal(str(emission_factor))
    co2e_kg = consumption_kwh * emission_factor_decimal

    activity_description = (
        f'Electricity - {address} '
        f'(Meter: {meter_id}, Account: {account_number})'
    )

    return {
        'success': True,
        'data': {
            'tenant_id': tenant_id,
            'raw_ingestion_id': raw_ingestion_id,
            'source_type': 'UTILITY',
            'source_row_reference': f'row_{row_num}',
            'scope': 2,
            'category': 'Purchased electricity',
            'activity_description': activity_description,
            'period_start': period_start,
            'period_end': period_end,
            'quantity_original': consumption_kwh,
            'unit_original': 'kWh',
            'quantity_normalized': consumption_kwh,
            'unit_normalized': 'kWh',
            'conversion_applied': 'No conversion needed',
            'emission_factor_used': emission_factor_decimal,
            'emission_factor_unit': 'kg CO2e per kWh',
            'emission_factor_source': 'BEIS 2023 / National Grid ESO',
            'co2e_kg': co2e_kg,
            'confidence_score': max(0.0, confidence),
            'flags': flags,
            'review_status': 'pending',
            'metadata': {
                'account_number': account_number,
                'meter_id': meter_id,
                'tariff_code': tariff,
                'meter_type': meter_type,
                'grid_region': grid_region,
            }
        }
    }