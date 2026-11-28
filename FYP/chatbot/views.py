import json
import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from FYP_app.models import LegacyAIAccess, Nominee, NomineeRole, UserProfile

from .models import (
    BeneficiaryPersona,
    LegacyConversation,
    LegacyMessage,
    MemoryChunk,
    MemorySource,
)
from .services import (
    EmbeddingUnavailable,
    categorize,
    crisis_response_for,
    embed_texts,
    extract_upload_text,
    generate_legacy_reply,
    get_readiness,
    split_into_chunks,
    retrieve_memories,
)

logger = logging.getLogger(__name__)
MAX_MANUAL_TEXT_CHARS = 50000
MAX_MESSAGE_CHARS = 2000


def _owner_access(nominee_id, owner):
    nominee = Nominee.objects.filter(id=nominee_id, user=owner).first()
    if nominee is None:
        return None, None
    has_beneficiary_role = NomineeRole.objects.filter(
        nominee=nominee,
        role='beneficiary',
        consent_status='accepted',
    ).exists()
    if not has_beneficiary_role:
        return nominee, Response(
            {'error': 'This contact must accept the beneficiary role first.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if not LegacyAIAccess.objects.filter(user=owner, nominee=nominee).exists():
        return nominee, Response(
            {'error': 'Assign Legacy AI access to this beneficiary first.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return nominee, None


def _is_active_owner(user):
    profile = UserProfile.objects.filter(user=user).first()
    return profile is None or profile.status == 'active'


def _beneficiary_access(user):
    nominee = Nominee.objects.filter(login_account=user).select_related('user').first()
    if nominee is None:
        return None, None, Response(
            {'error': 'This account is not linked to a beneficiary.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    accepted = NomineeRole.objects.filter(
        nominee=nominee,
        role='beneficiary',
        consent_status='accepted',
    ).exists()
    access = LegacyAIAccess.objects.filter(
        nominee=nominee,
        user=nominee.user,
    ).exists()
    profile = UserProfile.objects.filter(user=nominee.user).first()
    if not accepted or not access or profile is None or profile.status != 'released':
        return nominee, None, Response(
            {'error': 'Legacy AI is available only after beneficiary access and release safeguards are confirmed.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    persona = BeneficiaryPersona.objects.filter(
        owner=nominee.user,
        nominee=nominee,
    ).first()
    if persona is None:
        return nominee, None, Response(
            {'error': 'The owner has not prepared Legacy AI for this beneficiary.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not persona.owner_data_consent_at:
        return nominee, None, Response(
            {'error': 'The owner has not enabled AI processing for this experience.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return nominee, persona, None


def _persona_payload(persona):
    readiness = get_readiness(persona.nominee)
    return {
        'nominee_id': persona.nominee_id,
        'nominee_name': persona.nominee.nominee_name,
        'owner_name': persona.owner.get_full_name() or persona.owner.username,
        'bond_context': persona.bond_context,
        'voice_preferences': persona.voice_preferences,
        'spirituality_enabled': persona.spirituality_enabled,
        'faith_tradition': persona.faith_tradition,
        'owner_data_consent': bool(persona.owner_data_consent_at),
        'beneficiary_processing_consent': bool(persona.beneficiary_processing_consent_at),
        'beneficiary_spirituality_enabled': persona.beneficiary_spirituality_enabled,
        'beneficiary_faith_tradition': persona.beneficiary_faith_tradition,
        'readiness': readiness,
    }


def _beneficiary_payload(persona):
    return {
        'owner_name': persona.owner.get_full_name() or persona.owner.username,
        'owner_data_consent': bool(persona.owner_data_consent_at),
        'beneficiary_processing_consent': bool(persona.beneficiary_processing_consent_at),
        'spirituality_enabled': persona.spirituality_enabled,
        'faith_tradition': persona.faith_tradition,
        'beneficiary_spirituality_enabled': persona.beneficiary_spirituality_enabled,
        'readiness': get_readiness(persona.nominee),
    }


def _source_payload(source, nominee=None):
    chunks = source.chunks.all()
    if nominee is not None:
        chunks = chunks.filter(source__beneficiaries=nominee)
    return {
        'id': source.id,
        'display_name': source.display_name,
        'status': source.status,
        'error_message': source.error_message,
        'created_at': source.created_at,
        'chunk_count': chunks.count(),
        'word_count': sum(chunks.values_list('word_count', flat=True)),
    }


class OwnerPersonaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, nominee_id):
        nominee, error = _owner_access(nominee_id, request.user)
        if error:
            return error
        if nominee is None:
            return Response({'error': 'Beneficiary not found.'}, status=status.HTTP_404_NOT_FOUND)
        persona, _ = BeneficiaryPersona.objects.get_or_create(
            owner=request.user,
            nominee=nominee,
        )
        return Response(_persona_payload(persona))

    def put(self, request, nominee_id):
        return self._save(request, nominee_id)

    def patch(self, request, nominee_id):
        return self._save(request, nominee_id)

    def _save(self, request, nominee_id):
        nominee, error = _owner_access(nominee_id, request.user)
        if error:
            return error
        if nominee is None:
            return Response({'error': 'Beneficiary not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_active_owner(request.user):
            return Response(
                {'error': 'Legacy AI settings are locked once release verification begins.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        persona, _ = BeneficiaryPersona.objects.get_or_create(
            owner=request.user,
            nominee=nominee,
        )
        data = request.data
        bond_context = data.get('bond_context', persona.bond_context)
        voice_preferences = data.get('voice_preferences', persona.voice_preferences)
        faith_tradition = data.get('faith_tradition', persona.faith_tradition)
        if not isinstance(bond_context, str) or len(bond_context) > 4000:
            return Response({'error': 'Relationship context must be 4,000 characters or fewer.'}, status=400)
        if not isinstance(voice_preferences, str) or len(voice_preferences) > 500:
            return Response({'error': 'Voice preferences must be 500 characters or fewer.'}, status=400)
        if not isinstance(faith_tradition, str) or len(faith_tradition) > 120:
            return Response({'error': 'Faith tradition must be 120 characters or fewer.'}, status=400)

        spirituality_enabled = data.get('spirituality_enabled', persona.spirituality_enabled)
        if not isinstance(spirituality_enabled, bool):
            return Response({'error': 'spirituality_enabled must be true or false.'}, status=400)
        owner_consent = data.get('owner_data_consent')
        if owner_consent is not None and not isinstance(owner_consent, bool):
            return Response({'error': 'owner_data_consent must be true or false.'}, status=400)
        if spirituality_enabled and not faith_tradition.strip():
            return Response({'error': 'Enter the owner’s faith tradition to enable spiritual content.'}, status=400)

        persona.bond_context = bond_context
        persona.voice_preferences = voice_preferences
        persona.faith_tradition = faith_tradition.strip()
        persona.spirituality_enabled = spirituality_enabled
        if owner_consent is True:
            persona.owner_data_consent_at = timezone.now()
        elif owner_consent is False:
            persona.owner_data_consent_at = None
            persona.beneficiary_processing_consent_at = None
            persona.beneficiary_spirituality_enabled = False
            persona.beneficiary_faith_tradition = ''
        persona.save()
        return Response(_persona_payload(persona))


class OwnerSourcesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        nominee_id = request.query_params.get('nominee_id')
        if not nominee_id:
            return Response({'error': 'nominee_id is required.'}, status=400)
        if not nominee_id.isdecimal() or int(nominee_id) < 1:
            return Response({'error': 'nominee_id must be a positive integer.'}, status=400)
        nominee, error = _owner_access(nominee_id, request.user)
        if error:
            return error
        if nominee is None:
            return Response({'error': 'Beneficiary not found.'}, status=404)
        sources = MemorySource.objects.filter(
            user=request.user,
            beneficiaries=nominee,
        ).distinct().order_by('-created_at')
        return Response([_source_payload(source, nominee) for source in sources])

    def post(self, request):
        if not _is_active_owner(request.user):
            return Response({'error': 'Uploads are locked once release verification begins.'}, status=403)
        raw_ids = request.data.get('nominee_ids')
        try:
            nominee_ids = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
        except json.JSONDecodeError:
            return Response({'error': 'nominee_ids must be a JSON array.'}, status=400)
        if not isinstance(nominee_ids, list) or not nominee_ids:
            return Response({'error': 'Choose at least one beneficiary for this memory.'}, status=400)
        if any(
            isinstance(nominee_id, bool)
            or not (
                isinstance(nominee_id, int)
                or isinstance(nominee_id, str) and nominee_id.isdecimal()
            )
            or int(nominee_id) < 1
            for nominee_id in nominee_ids
        ):
            return Response({'error': 'Each beneficiary ID must be a positive integer.'}, status=400)
        nominee_ids = [int(nominee_id) for nominee_id in nominee_ids]
        if len(set(nominee_ids)) != len(nominee_ids):
            return Response({'error': 'A beneficiary may only be selected once.'}, status=400)

        nominees = []
        for nominee_id in nominee_ids:
            nominee, error = _owner_access(nominee_id, request.user)
            if error:
                return error
            if nominee is None:
                return Response({'error': 'One or more selected beneficiaries do not belong to this account.'}, status=403)
            persona = BeneficiaryPersona.objects.filter(owner=request.user, nominee=nominee).first()
            if persona is None or not persona.owner_data_consent_at:
                return Response(
                    {'error': f'Enable and save local AI processing consent for {nominee.nominee_name} first.'},
                    status=403,
                )
            nominees.append(nominee)

        upload = request.FILES.get('file')
        typed_text = request.data.get('text')
        if bool(upload) == bool(typed_text):
            return Response({'error': 'Provide exactly one PDF/TXT/Markdown file or pasted text.'}, status=400)
        if typed_text:
            if not isinstance(typed_text, str) or len(typed_text) > MAX_MANUAL_TEXT_CHARS:
                return Response({'error': 'Pasted text must be 50,000 characters or fewer.'}, status=400)
            text = typed_text.strip()
            display_name = str(request.data.get('display_name') or 'Personal notes')[:200]
            if not text:
                return Response({'error': 'Add some text before uploading.'}, status=400)
        else:
            try:
                text = extract_upload_text(upload)
            except ValueError as error:
                return Response({'error': str(error)}, status=400)
            display_name = upload.name[:200]

        chunks = split_into_chunks(text)
        try:
            embeddings = embed_texts(chunks)
        except EmbeddingUnavailable as error:
            return Response({'error': str(error)}, status=503)
        if len(chunks) != len(embeddings):
            logger.error('Local embedding model returned %s vectors for %s memory chunks.', len(embeddings), len(chunks))
            return Response({'error': 'Memory indexing returned incomplete results. Please retry.'}, status=503)

        try:
            with transaction.atomic():
                source = MemorySource.objects.create(
                    user=request.user,
                    display_name=display_name,
                    file=upload if upload else None,
                    status='ready',
                )
                source.beneficiaries.set(nominees)
                MemoryChunk.objects.bulk_create([
                    MemoryChunk(
                        source=source,
                        text=chunk,
                        category=categorize(chunk),
                        word_count=len(chunk.split()),
                        embedding=embedding,
                    )
                    for chunk, embedding in zip(chunks, embeddings)
                ])
        except OSError:
            logger.exception('Could not store a Legacy AI memory source for owner %s.', request.user.pk)
            return Response({'error': 'The upload could not be stored. Check server storage and try again.'}, status=500)
        return Response(
            {
                'source': _source_payload(source),
                'beneficiaries': [
                    {'id': nominee.id, 'readiness': get_readiness(nominee)}
                    for nominee in nominees
                ],
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request):
        source_id = request.data.get('source_id') or request.query_params.get('source_id')
        if not source_id:
            return Response({'error': 'source_id is required.'}, status=400)
        if not str(source_id).isdecimal() or int(source_id) < 1:
            return Response({'error': 'source_id must be a positive integer.'}, status=400)
        source = MemorySource.objects.filter(user=request.user, id=source_id).first()
        if source is None:
            return Response({'error': 'Memory source not found.'}, status=404)
        if not _is_active_owner(request.user):
            return Response({'error': 'Memory sources cannot be changed once release verification begins.'}, status=403)
        source.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OwnerReadinessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, nominee_id):
        nominee, error = _owner_access(nominee_id, request.user)
        if error:
            return error
        if nominee is None:
            return Response({'error': 'Beneficiary not found.'}, status=404)
        sources = MemorySource.objects.filter(
            user=request.user,
            beneficiaries=nominee,
        ).distinct().order_by('-created_at')
        return Response({
            'readiness': get_readiness(nominee),
            'sources': [_source_payload(source, nominee) for source in sources],
        })


class OwnerPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, nominee_id):
        nominee, error = _owner_access(nominee_id, request.user)
        if error:
            return error
        if nominee is None:
            return Response({'error': 'Beneficiary not found.'}, status=404)
        if not _is_active_owner(request.user):
            return Response(
                {'error': 'Legacy AI preview is locked once release verification begins.'},
                status=403,
            )

        persona = BeneficiaryPersona.objects.filter(
            owner=request.user,
            nominee=nominee,
        ).first()
        if persona is None or not persona.owner_data_consent_at:
            return Response(
                {'error': 'Save local AI processing consent before testing Legacy AI.'},
                status=403,
            )

        question = request.data.get('message')
        if not isinstance(question, str) or not question.strip() or len(question) > MAX_MESSAGE_CHARS:
            return Response({'error': 'Message must contain 1–2,000 characters.'}, status=400)

        raw_history = request.data.get('history', [])
        if not isinstance(raw_history, list) or len(raw_history) > 6:
            return Response({'error': 'Preview history must contain at most six messages.'}, status=400)
        history = []
        for item in raw_history:
            if (
                not isinstance(item, dict)
                or item.get('role') not in {'user', 'assistant'}
                or not isinstance(item.get('content'), str)
                or not item['content'].strip()
                or len(item['content']) > MAX_MESSAGE_CHARS
            ):
                return Response({'error': 'Preview history contains an invalid message.'}, status=400)
            history.append({
                'role': item['role'],
                'content': item['content'].strip(),
            })

        question = question.strip()
        readiness = get_readiness(nominee)
        try:
            answer = crisis_response_for(question)
            if answer is None:
                memories = retrieve_memories(nominee, question)
                answer = generate_legacy_reply(
                    persona,
                    question,
                    memories,
                    readiness,
                    conversation_history=history,
                )
        except EmbeddingUnavailable as error:
            return Response({'error': str(error)}, status=503)
        except RuntimeError as error:
            return Response({'error': str(error)}, status=503)

        return Response({
            'message': {'role': 'assistant', 'content': answer},
            'readiness': readiness,
            'saved': False,
        })


class BeneficiaryProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        nominee, persona, error = _beneficiary_access(request.user)
        if error:
            return error
        return Response(_beneficiary_payload(persona))


class BeneficiaryConsentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        nominee, persona, error = _beneficiary_access(request.user)
        if error:
            return error
        accepted = request.data.get('accepted')
        if not isinstance(accepted, bool):
            return Response({'error': 'accepted must be true or false.'}, status=400)
        enabled = request.data.get('spirituality_enabled', False)
        tradition = request.data.get('faith_tradition', '')
        if not isinstance(enabled, bool) or not isinstance(tradition, str) or len(tradition) > 120:
            return Response({'error': 'Spiritual preferences are invalid.'}, status=400)
        if enabled and not tradition.strip():
            return Response({'error': 'Enter your faith tradition to enable spiritual content.'}, status=400)
        persona.beneficiary_processing_consent_at = timezone.now() if accepted else None
        persona.beneficiary_spirituality_enabled = enabled if accepted else False
        persona.beneficiary_faith_tradition = tradition.strip() if accepted and enabled else ''
        persona.save(update_fields=[
            'beneficiary_processing_consent_at',
            'beneficiary_spirituality_enabled',
            'beneficiary_faith_tradition',
            'updated_at',
        ])
        if not accepted:
            LegacyConversation.objects.filter(
                owner=nominee.user,
                nominee=nominee,
            ).delete()
        return Response({
            'accepted': bool(persona.beneficiary_processing_consent_at),
            'spirituality_enabled': persona.beneficiary_spirituality_enabled,
            'faith_tradition': persona.beneficiary_faith_tradition,
        })


class BeneficiaryChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        nominee, persona, error = _beneficiary_access(request.user)
        if error:
            return error
        if not persona.beneficiary_processing_consent_at:
            return Response({'error': 'Review and accept the local AI processing notice before chatting.'}, status=403)
        conversation, _ = LegacyConversation.objects.get_or_create(
            owner=nominee.user,
            nominee=nominee,
        )
        messages = conversation.messages.order_by('created_at', 'id')
        return Response({
            'readiness': get_readiness(nominee),
            'messages': [
                {'role': message.role, 'content': message.content, 'created_at': message.created_at}
                for message in messages
            ],
        })

    def post(self, request):
        nominee, persona, error = _beneficiary_access(request.user)
        if error:
            return error
        if not persona.beneficiary_processing_consent_at:
            return Response({'error': 'Review and accept the local AI processing notice before chatting.'}, status=403)
        content = request.data.get('message')
        if not isinstance(content, str) or not content.strip() or len(content) > MAX_MESSAGE_CHARS:
            return Response({'error': 'Message must contain 1–2,000 characters.'}, status=400)

        readiness = get_readiness(nominee)
        try:
            question = content.strip()
            answer = crisis_response_for(question)
            if answer is None:
                memories = retrieve_memories(nominee, question)
                conversation = LegacyConversation.objects.filter(
                    owner=nominee.user,
                    nominee=nominee,
                ).first()
                history = []
                if conversation is not None:
                    history = [
                        {'role': message.role, 'content': message.content}
                        for message in conversation.messages.order_by('-created_at', '-id')[:6][::-1]
                    ]
                answer = generate_legacy_reply(
                    persona,
                    question,
                    memories,
                    readiness,
                    conversation_history=history,
                )
        except EmbeddingUnavailable as error:
            return Response({'error': str(error)}, status=503)
        except RuntimeError as error:
            return Response({'error': str(error)}, status=503)

        with transaction.atomic():
            conversation, _ = LegacyConversation.objects.get_or_create(
                owner=nominee.user,
                nominee=nominee,
            )
            LegacyMessage.objects.bulk_create([
                LegacyMessage(conversation=conversation, role='user', content=content.strip()),
                LegacyMessage(conversation=conversation, role='assistant', content=answer),
            ])
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
        return Response({
            'message': {'role': 'assistant', 'content': answer},
            'readiness': readiness,
        })
