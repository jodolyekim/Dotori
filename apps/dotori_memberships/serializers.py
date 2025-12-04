from rest_framework import serializers
from .models import MembershipPlan, UserMembership, PointWallet, PointTransaction


class MembershipPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipPlan
        fields = "__all__"


class UserMembershipSerializer(serializers.ModelSerializer):
    plan = MembershipPlanSerializer()

    class Meta:
        model = UserMembership
        fields = ["plan", "started_at", "expires_at", "is_active"]


class PointWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointWallet
        fields = ["balance"]


class PointTransactionSerializer(serializers.ModelSerializer):
    signed_amount = serializers.SerializerMethodField()

    def get_signed_amount(self, obj):
        return obj.signed_amount()

    class Meta:
        model = PointTransaction
        fields = [
            "id",
            "tx_type",
            "amount",
            "signed_amount",
            "reason",
            "description",
            "created_at",
        ]
