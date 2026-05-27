from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import RawIngestion
from .parsers.sap_parser import parse_sap_file
from .parsers.utility_parser import parse_utility_file
from .parsers.travel_parser import parse_travel_file
from emissions.models import NormalizedEmission, EmissionAuditLog


def _run_ingestion(request, source_type, parse_fn, decode='utf-8'):
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided'}, status=400)

    try:
        content = file.read().decode(decode, errors='replace')
    except Exception as e:
        return Response({'error': f'Could not read file: {str(e)}'}, status=400)

    raw_ingestion = RawIngestion.objects.create(
        tenant=request.user.tenant,
        source_type=source_type,
        original_filename=file.name,
        uploaded_by=request.user,
        raw_content={'raw_text': content[:50000]},  # Store first 50k chars
        status='processing',
    )

    successes, errors = parse_fn(
        content,
        raw_ingestion.id,
        request.user.tenant.id
    )

    emission_objects = []
    for data in successes:
        emission_objects.append(NormalizedEmission(**data))

    created = NormalizedEmission.objects.bulk_create(emission_objects)

    # Create audit log entries for each created emission
    audit_entries = []
    for emission in created:
        audit_entries.append(EmissionAuditLog(
            emission=emission,
            action='created',
            performed_by=request.user,
            new_value={'source': source_type, 'filename': file.name},
        ))
    EmissionAuditLog.objects.bulk_create(audit_entries)

    raw_ingestion.status = 'completed' if not errors else 'partial'
    raw_ingestion.row_count_total = len(successes) + len(errors)
    raw_ingestion.row_count_success = len(successes)
    raw_ingestion.row_count_failed = len(errors)
    raw_ingestion.error_log = errors
    raw_ingestion.save()

    return Response({
        'ingestion_id': str(raw_ingestion.id),
        'rows_processed': len(successes),
        'rows_failed': len(errors),
        'errors': errors[:20],  # Return first 20 errors max
    }, status=201)


class SAPUploadView(APIView):
    def post(self, request):
        return _run_ingestion(request, 'SAP', parse_sap_file)


class UtilityUploadView(APIView):
    def post(self, request):
        return _run_ingestion(request, 'UTILITY', parse_utility_file)


class TravelUploadView(APIView):
    def post(self, request):
        return _run_ingestion(request, 'TRAVEL', parse_travel_file)


class IngestionListView(APIView):
    def get(self, request):
        ingestions = RawIngestion.objects.filter(
            tenant=request.user.tenant
        ).values(
            'id', 'source_type', 'original_filename',
            'uploaded_at', 'status',
            'row_count_total', 'row_count_success', 'row_count_failed'
        )
        return Response(list(ingestions))