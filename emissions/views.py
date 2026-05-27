from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import NormalizedEmission, EmissionAuditLog


class EmissionListView(APIView):

    def get(self, request):
        qs = NormalizedEmission.objects.filter(tenant=request.user.tenant)

        # Filters
        source = request.query_params.get('source')
        scope = request.query_params.get('scope')
        review_status = request.query_params.get('status')
        flagged = request.query_params.get('flagged')

        if source:
            qs = qs.filter(source_type=source)
        if scope:
            qs = qs.filter(scope=scope)
        if review_status:
            qs = qs.filter(review_status=review_status)
        if flagged == 'true':
            # JSONField: filter rows where flags list is not empty
            qs = qs.exclude(flags=[])

        data = list(qs.values(
            'id', 'source_type', 'scope', 'category',
            'activity_description', 'period_start', 'period_end',
            'co2e_kg', 'confidence_score', 'flags',
            'review_status', 'reviewed_at',
            'unit_original', 'quantity_original',
            'unit_normalized', 'quantity_normalized',
            'emission_factor_used', 'emission_factor_source',
            'conversion_applied', 'created_at',
        ))

        return Response(data)


class EmissionDetailView(APIView):

    def get(self, request, pk):
        emission = get_object_or_404(
            NormalizedEmission, pk=pk, tenant=request.user.tenant
        )
        audit_logs = list(
            emission.audit_logs.values(
                'action', 'performed_by__username',
                'performed_at', 'previous_value', 'new_value', 'note'
            )
        )
        raw_data = {
            'id': str(emission.id),
            'source_type': emission.source_type,
            'scope': emission.scope,
            'category': emission.category,
            'activity_description': emission.activity_description,
            'period_start': emission.period_start,
            'period_end': emission.period_end,
            'quantity_original': str(emission.quantity_original),
            'unit_original': emission.unit_original,
            'quantity_normalized': str(emission.quantity_normalized),
            'unit_normalized': emission.unit_normalized,
            'conversion_applied': emission.conversion_applied,
            'emission_factor_used': str(emission.emission_factor_used),
            'emission_factor_unit': emission.emission_factor_unit,
            'emission_factor_source': emission.emission_factor_source,
            'co2e_kg': str(emission.co2e_kg),
            'confidence_score': emission.confidence_score,
            'flags': emission.flags,
            'review_status': emission.review_status,
            'review_note': emission.review_note,
            'metadata': emission.metadata,
            'created_at': emission.created_at,
            'updated_at': emission.updated_at,
            'audit_logs': audit_logs,
        }
        return Response(raw_data)

    def patch(self, request, pk):
        """Allow analyst to edit co2e_kg or add a note."""
        emission = get_object_or_404(
            NormalizedEmission, pk=pk, tenant=request.user.tenant
        )

        if emission.review_status == 'locked':
            return Response(
                {'error': 'Cannot edit a locked emission'},
                status=400
            )

        allowed_fields = ['co2e_kg', 'review_note', 'emission_factor_used']
        previous = {}
        new = {}

        for field in allowed_fields:
            if field in request.data:
                previous[field] = str(getattr(emission, field))
                setattr(emission, field, request.data[field])
                new[field] = request.data[field]

        emission.save()

        EmissionAuditLog.objects.create(
            emission=emission,
            action='edited',
            performed_by=request.user,
            previous_value=previous,
            new_value=new,
        )

        return Response({'status': 'updated'})


class EmissionApproveView(APIView):

    def post(self, request, pk):
        emission = get_object_or_404(
            NormalizedEmission, pk=pk, tenant=request.user.tenant
        )
        if emission.review_status == 'locked':
            return Response({'error': 'Already locked'}, status=400)

        emission.review_status = 'approved'
        emission.reviewed_by = request.user
        emission.reviewed_at = timezone.now()
        emission.review_note = request.data.get('note', '')
        emission.save()

        EmissionAuditLog.objects.create(
            emission=emission,
            action='approved',
            performed_by=request.user,
            note=emission.review_note,
        )
        return Response({'status': 'approved'})


class EmissionRejectView(APIView):

    def post(self, request, pk):
        emission = get_object_or_404(
            NormalizedEmission, pk=pk, tenant=request.user.tenant
        )
        if emission.review_status == 'locked':
            return Response({'error': 'Already locked'}, status=400)

        note = request.data.get('note', '')
        if not note:
            return Response(
                {'error': 'A note is required when rejecting'},
                status=400
            )

        emission.review_status = 'rejected'
        emission.reviewed_by = request.user
        emission.reviewed_at = timezone.now()
        emission.review_note = note
        emission.save()

        EmissionAuditLog.objects.create(
            emission=emission,
            action='rejected',
            performed_by=request.user,
            note=note,
        )
        return Response({'status': 'rejected'})


class EmissionLockView(APIView):

    def post(self, request, pk):
        emission = get_object_or_404(
            NormalizedEmission, pk=pk, tenant=request.user.tenant
        )
        if emission.review_status != 'approved':
            return Response(
                {'error': 'Only approved emissions can be locked'},
                status=400
            )

        emission.review_status = 'locked'
        emission.locked_at = timezone.now()
        emission.locked_by = request.user
        emission.save()

        EmissionAuditLog.objects.create(
            emission=emission,
            action='locked',
            performed_by=request.user,
        )
        return Response({'status': 'locked'})


class DashboardSummaryView(APIView):

    def get(self, request):
        from django.db.models import Count, Sum

        tenant = request.user.tenant
        qs = NormalizedEmission.objects.filter(tenant=tenant)

        summary = {
            'total_rows': qs.count(),
            'pending': qs.filter(review_status='pending').count(),
            'approved': qs.filter(review_status='approved').count(),
            'rejected': qs.filter(review_status='rejected').count(),
            'locked': qs.filter(review_status='locked').count(),
            'flagged': qs.exclude(flags=[]).count(),
            'total_co2e_kg': float(
                qs.aggregate(t=Sum('co2e_kg'))['t'] or 0
            ),
            'by_scope': list(
                qs.values('scope')
                .annotate(count=Count('id'), co2e_kg=Sum('co2e_kg'))
                .order_by('scope')
            ),
            'by_source': list(
                qs.values('source_type')
                .annotate(count=Count('id'), co2e_kg=Sum('co2e_kg'))
            ),
        }

        return Response(summary)