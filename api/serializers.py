from rest_framework import serializers

from registry.models import Nurse


class PublicNurseSerializer(serializers.ModelSerializer):
    licence_status = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    employer = serializers.SerializerMethodField()

    class Meta:
        model = Nurse
        fields = (
            "nanm_id",
            "full_name",
            "photo_url",
            "licence_status",
            "licence_expiry",
            "employer",
            "record_status",
        )

    def get_licence_status(self, obj):
        return obj.public_licence_status

    def get_photo_url(self, obj):
        if not obj.photo:
            return ""
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(obj.photo.url)
        return obj.photo.url

    def get_employer(self, obj):
        return obj.employer.name if obj.employer else ""
