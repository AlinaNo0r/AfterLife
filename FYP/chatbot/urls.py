from django.urls import path

from .views import (
    BeneficiaryChatView,
    BeneficiaryConsentView,
    BeneficiaryProfileView,
    OwnerPersonaView,
    OwnerPreviewView,
    OwnerReadinessView,
    OwnerSourcesView,
)

urlpatterns = [
    path('owner/personas/<int:nominee_id>/', OwnerPersonaView.as_view(), name='legacy-ai-persona'),
    path('owner/readiness/<int:nominee_id>/', OwnerReadinessView.as_view(), name='legacy-ai-readiness'),
    path('owner/preview/<int:nominee_id>/', OwnerPreviewView.as_view(), name='legacy-ai-preview'),
    path('owner/sources/', OwnerSourcesView.as_view(), name='legacy-ai-sources'),
    path('beneficiary/', BeneficiaryProfileView.as_view(), name='legacy-ai-beneficiary'),
    path('beneficiary/consent/', BeneficiaryConsentView.as_view(), name='legacy-ai-beneficiary-consent'),
    path('beneficiary/chat/', BeneficiaryChatView.as_view(), name='legacy-ai-beneficiary-chat'),
]
