from django.contrib import admin

from .models import (
    BeneficiaryPersona,
    LegacyConversation,
    LegacyMessage,
    MemoryChunk,
    MemorySource,
)

admin.site.register(MemorySource)
admin.site.register(MemoryChunk)
admin.site.register(BeneficiaryPersona)
admin.site.register(LegacyConversation)
admin.site.register(LegacyMessage)
