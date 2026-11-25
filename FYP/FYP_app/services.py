import uuid

from django.utils import timezone

from .emails import send_nominee_invitation_email


def send_pending_role_invitations(nominee, owner_name, resend=False):
    results = []
    roles = nominee.roles.filter(consent_status='pending').order_by('role')

    for role in roles:
        if role.invitation_sent_at and not resend:
            continue
        if resend:
            role.invitation_token = uuid.uuid4()
            role.save(update_fields=['invitation_token'])

        sent = send_nominee_invitation_email(role, owner_name)
        if sent:
            role.invitation_sent_at = timezone.now()
            role.save(update_fields=['invitation_sent_at'])
        results.append({'role': role.role, 'sent': sent})

    return {
        'sent': all(result['sent'] for result in results),
        'roles': results,
    }