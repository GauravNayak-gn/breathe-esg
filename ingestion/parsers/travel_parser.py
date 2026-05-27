import json
import math
from decimal import Decimal
from datetime import datetime

# Airport coordinates for haversine calculation
# Source: OurAirports database (ourairports.com/data/)
AIRPORT_COORDS = {
    'LHR': (51.4775, -0.4614),
    'JFK': (40.6413, -73.7781),
    'SIN': (1.3644, 103.9915),
    'CDG': (49.0097, 2.5478),
    'DXB': (25.2532, 55.3657),
    'ORD': (41.9742, -87.9073),
    'LAX': (33.9425, -118.4081),
    'FRA': (50.0379, 8.5622),
    'AMS': (52.3086, 4.7639),
    'HKG': (22.3080, 113.9185),
}

SHORT_HAUL_MAX_KM = 3700


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate great circle distance between two points.
    Returns distance in km.
    """
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def get_haul_type(distance_km):
    return 'short' if distance_km <= SHORT_HAUL_MAX_KM else 'long'


def parse_travel_file(file_content, raw_ingestion_id, tenant_id):
    """
    Parse corporate travel JSON export.
    Returns (successes, errors).
    Each segment becomes one NormalizedEmission row.
    """
    from emissions.emission_factors import (
        FLIGHT_FACTORS,
        HOTEL_NIGHT_UK,
        HOTEL_NIGHT_INTERNATIONAL,
        GROUND_TRANSPORT,
        TAXI_DEFAULT_KM,
    )

    successes = []
    errors = []

    try:
        data = json.loads(file_content)
    except json.JSONDecodeError as e:
        return [], [{'row': 0, 'error': f'Invalid JSON: {str(e)}', 'raw': {}}]

    trips = data.get('trips', [])

    for trip in trips:
        trip_id = trip.get('trip_id', 'unknown')
        employee_id = trip.get('employee_id', '')
        department = trip.get('department', '')
        cost_center = trip.get('cost_center', '')
        segments = trip.get('segments', [])

        for segment in segments:
            seg_id = segment.get('segment_id', 'unknown')
            seg_type = segment.get('type', '')

            try:
                if seg_type == 'flight':
                    result = _process_flight(
                        segment, trip_id, seg_id,
                        employee_id, department, cost_center,
                        raw_ingestion_id, tenant_id
                    )
                elif seg_type == 'hotel':
                    result = _process_hotel(
                        segment, trip_id, seg_id,
                        employee_id, department, cost_center,
                        raw_ingestion_id, tenant_id
                    )
                elif seg_type == 'ground':
                    result = _process_ground(
                        segment, trip_id, seg_id,
                        employee_id, department, cost_center,
                        raw_ingestion_id, tenant_id
                    )
                else:
                    errors.append({
                        'row': seg_id,
                        'error': f'Unknown segment type: {seg_type}',
                        'raw': segment
                    })
                    continue

                if result['success']:
                    successes.append(result['data'])
                else:
                    errors.append(result['error'])

            except Exception as e:
                errors.append({
                    'row': seg_id,
                    'error': f'Unexpected error: {str(e)}',
                    'raw': segment
                })

    return successes, errors


def _process_flight(segment, trip_id, seg_id, employee_id, department,
                    cost_center, raw_ingestion_id, tenant_id):
    from emissions.emission_factors import FLIGHT_FACTORS

    flags = []
    confidence = 1.0

    origin = (segment.get('origin') or '').strip().upper()
    destination = (segment.get('destination') or '').strip().upper()
    cabin_class = (segment.get('cabin_class') or 'economy').strip().lower()
    departure_date_str = segment.get('departure_date', '')
    distance_km = segment.get('distance_km')

    try:
        departure_date = datetime.strptime(departure_date_str, '%Y-%m-%d').date()
    except ValueError:
        return {
            'success': False,
            'error': {
                'row': seg_id,
                'error': f'Invalid departure_date: {departure_date_str}',
                'raw': segment
            }
        }

    # Calculate distance if not provided
    if distance_km is None:
        origin_coords = AIRPORT_COORDS.get(origin)
        dest_coords = AIRPORT_COORDS.get(destination)

        if origin_coords and dest_coords:
            distance_km = haversine_km(
                origin_coords[0], origin_coords[1],
                dest_coords[0], dest_coords[1]
            )
            flags.append(
                f'Distance calculated via haversine formula from airport coordinates. '
                f'Actual flight path may differ.'
            )
            confidence -= 0.05
        else:
            missing = []
            if not origin_coords:
                missing.append(origin)
            if not dest_coords:
                missing.append(destination)
            flags.append(
                f'Airport coordinates not found for: {", ".join(missing)}. '
                f'Cannot calculate distance. CO2e not calculated.'
            )
            confidence = 0.0
            return {
                'success': True,
                'data': _build_emission_row(
                    tenant_id=tenant_id,
                    raw_ingestion_id=raw_ingestion_id,
                    source_row_reference=seg_id,
                    scope=3,
                    category='Business travel - flights',
                    activity_description=f'Flight {origin} to {destination} ({cabin_class})',
                    period_start=departure_date,
                    period_end=departure_date,
                    quantity_original=None,
                    unit_original='km',
                    quantity_normalized=None,
                    unit_normalized='km',
                    conversion_applied='',
                    emission_factor_used=None,
                    emission_factor_unit='kg CO2e per passenger km',
                    emission_factor_source='DEFRA 2023',
                    co2e_kg=None,
                    confidence_score=0.0,
                    flags=flags,
                    metadata={
                        'trip_id': trip_id,
                        'employee_id': employee_id,
                        'department': department,
                        'cost_center': cost_center,
                        'origin': origin,
                        'destination': destination,
                        'cabin_class': cabin_class,
                        'carrier': segment.get('carrier', ''),
                        'flight_number': segment.get('flight_number', ''),
                    }
                )
            }

    haul_type = get_haul_type(distance_km)
    factor_key = (cabin_class, haul_type)
    emission_factor = FLIGHT_FACTORS.get(factor_key)

    if emission_factor is None:
        flags.append(
            f'No emission factor for cabin class {cabin_class}, haul {haul_type}. '
            f'Defaulting to economy long haul.'
        )
        emission_factor = FLIGHT_FACTORS[('economy', 'long')]
        confidence -= 0.2

    distance_decimal = Decimal(str(round(distance_km, 2)))
    ef_decimal = Decimal(str(emission_factor))
    co2e_kg = distance_decimal * ef_decimal

    activity_description = (
        f'Flight {origin} to {destination} ({cabin_class}, {haul_type} haul) '
        f'- {employee_id} ({department})'
    )

    return {
        'success': True,
        'data': _build_emission_row(
            tenant_id=tenant_id,
            raw_ingestion_id=raw_ingestion_id,
            source_row_reference=seg_id,
            scope=3,
            category='Business travel - flights',
            activity_description=activity_description,
            period_start=departure_date,
            period_end=departure_date,
            quantity_original=distance_decimal,
            unit_original='km',
            quantity_normalized=distance_decimal,
            unit_normalized='km',
            conversion_applied='Haversine formula from IATA airport coordinates'
            if segment.get('distance_km') is None else 'Distance provided by platform',
            emission_factor_used=ef_decimal,
            emission_factor_unit='kg CO2e per passenger km',
            emission_factor_source='DEFRA 2023',
            co2e_kg=co2e_kg,
            confidence_score=max(0.0, confidence),
            flags=flags,
            metadata={
                'trip_id': trip_id,
                'employee_id': employee_id,
                'department': department,
                'cost_center': cost_center,
                'origin': origin,
                'destination': destination,
                'cabin_class': cabin_class,
                'haul_type': haul_type,
                'carrier': segment.get('carrier', ''),
                'flight_number': segment.get('flight_number', ''),
                'distance_km': round(distance_km, 2),
            }
        )
    }


def _process_hotel(segment, trip_id, seg_id, employee_id, department,
                   cost_center, raw_ingestion_id, tenant_id):
    from emissions.emission_factors import HOTEL_NIGHT_UK, HOTEL_NIGHT_INTERNATIONAL

    flags = []
    confidence = 1.0

    country = (segment.get('country') or '').strip().upper()
    city = (segment.get('city') or '').strip()
    property_name = (segment.get('property_name') or '').strip()
    nights = segment.get('nights')
    check_in_str = segment.get('check_in', '')

    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(segment.get('check_out', ''), '%Y-%m-%d').date()
    except ValueError:
        return {
            'success': False,
            'error': {
                'row': seg_id,
                'error': f'Invalid hotel dates',
                'raw': segment
            }
        }

    if nights is None:
        nights = (check_out - check_in).days
        flags.append('Night count calculated from check-in/check-out dates')

    emission_factor = HOTEL_NIGHT_UK if country == 'GB' else HOTEL_NIGHT_INTERNATIONAL
    ef_decimal = Decimal(str(emission_factor))
    nights_decimal = Decimal(str(nights))
    co2e_kg = nights_decimal * ef_decimal

    activity_description = (
        f'Hotel - {property_name}, {city} ({nights} nights) '
        f'- {employee_id} ({department})'
    )

    return {
        'success': True,
        'data': _build_emission_row(
            tenant_id=tenant_id,
            raw_ingestion_id=raw_ingestion_id,
            source_row_reference=seg_id,
            scope=3,
            category='Business travel - hotels',
            activity_description=activity_description,
            period_start=check_in,
            period_end=check_out,
            quantity_original=nights_decimal,
            unit_original='nights',
            quantity_normalized=nights_decimal,
            unit_normalized='nights',
            conversion_applied='No conversion needed',
            emission_factor_used=ef_decimal,
            emission_factor_unit='kg CO2e per room night',
            emission_factor_source='DEFRA 2023',
            co2e_kg=co2e_kg,
            confidence_score=confidence,
            flags=flags,
            metadata={
                'trip_id': trip_id,
                'employee_id': employee_id,
                'department': department,
                'cost_center': cost_center,
                'property_name': property_name,
                'city': city,
                'country': country,
            }
        )
    }


def _process_ground(segment, trip_id, seg_id, employee_id, department,
                    cost_center, raw_ingestion_id, tenant_id):
    from emissions.emission_factors import GROUND_TRANSPORT, TAXI_DEFAULT_KM

    flags = []
    confidence = 1.0

    subtype = (segment.get('subtype') or 'taxi').strip().lower()
    city = (segment.get('city') or '').strip()
    country = (segment.get('country') or '').strip()
    date_str = segment.get('date', '')
    distance_km = segment.get('distance_km')

    try:
        travel_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return {
            'success': False,
            'error': {
                'row': seg_id,
                'error': f'Invalid ground transport date: {date_str}',
                'raw': segment
            }
        }

    if distance_km is None:
        distance_km = TAXI_DEFAULT_KM
        flags.append(
            f'Distance not provided. Applied default of {TAXI_DEFAULT_KM} km. '
            f'This is an estimate and should be verified.'
        )
        confidence -= 0.4

    emission_factor = GROUND_TRANSPORT.get(subtype, GROUND_TRANSPORT['taxi'])
    if subtype not in GROUND_TRANSPORT:
        flags.append(
            f'Unknown ground transport subtype: {subtype}. '
            f'Using taxi emission factor as default.'
        )
        confidence -= 0.2

    distance_decimal = Decimal(str(distance_km))
    ef_decimal = Decimal(str(emission_factor))
    co2e_kg = distance_decimal * ef_decimal

    activity_description = (
        f'{subtype.title()} - {city}, {country} '
        f'- {employee_id} ({department})'
    )

    return {
        'success': True,
        'data': _build_emission_row(
            tenant_id=tenant_id,
            raw_ingestion_id=raw_ingestion_id,
            source_row_reference=seg_id,
            scope=3,
            category=f'Business travel - ground ({subtype})',
            activity_description=activity_description,
            period_start=travel_date,
            period_end=travel_date,
            quantity_original=distance_decimal,
            unit_original='km',
            quantity_normalized=distance_decimal,
            unit_normalized='km',
            conversion_applied='No conversion needed',
            emission_factor_used=ef_decimal,
            emission_factor_unit='kg CO2e per km',
            emission_factor_source='DEFRA 2023',
            co2e_kg=co2e_kg,
            confidence_score=max(0.0, confidence),
            flags=flags,
            metadata={
                'trip_id': trip_id,
                'employee_id': employee_id,
                'department': department,
                'cost_center': cost_center,
                'subtype': subtype,
                'city': city,
                'country': country,
            }
        )
    }


def _build_emission_row(**kwargs):
    """Helper to ensure consistent dict structure for all segment types."""
    return {
        'tenant_id': kwargs['tenant_id'],
        'raw_ingestion_id': kwargs['raw_ingestion_id'],
        'source_type': 'TRAVEL',
        'source_row_reference': kwargs['source_row_reference'],
        'scope': kwargs['scope'],
        'category': kwargs['category'],
        'activity_description': kwargs['activity_description'],
        'period_start': kwargs['period_start'],
        'period_end': kwargs['period_end'],
        'quantity_original': kwargs.get('quantity_original'),
        'unit_original': kwargs.get('unit_original', ''),
        'quantity_normalized': kwargs.get('quantity_normalized'),
        'unit_normalized': kwargs.get('unit_normalized', ''),
        'conversion_applied': kwargs.get('conversion_applied', ''),
        'emission_factor_used': kwargs.get('emission_factor_used'),
        'emission_factor_unit': kwargs.get('emission_factor_unit', ''),
        'emission_factor_source': kwargs.get('emission_factor_source', ''),
        'co2e_kg': kwargs.get('co2e_kg'),
        'confidence_score': kwargs.get('confidence_score', 1.0),
        'flags': kwargs.get('flags', []),
        'review_status': 'pending',
        'metadata': kwargs.get('metadata', {}),
    }