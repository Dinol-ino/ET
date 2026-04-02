"""initial schema for sales intelligence backend

Revision ID: 0001_initial
Revises: 
Create Date: 2026-04-02 23:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("job_title", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contacts_email"), "contacts", ["email"], unique=False)
    op.create_index(op.f("ix_contacts_external_id"), "contacts", ["external_id"], unique=True)

    op.create_table(
        "prospect_analysis",
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scraped_excerpt", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("outreach_message", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prospect_analysis_company_name"), "prospect_analysis", ["company_name"], unique=False)
    op.create_index(op.f("ix_prospect_analysis_domain"), "prospect_analysis", ["domain"], unique=False)

    op.create_table(
        "deals",
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("stage", sa.String(length=120), nullable=True),
        sa.Column("pipeline", sa.String(length=120), nullable=True),
        sa.Column("close_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deals_contact_id"), "deals", ["contact_id"], unique=False)
    op.create_index(op.f("ix_deals_external_id"), "deals", ["external_id"], unique=True)
    op.create_index(op.f("ix_deals_last_activity_at"), "deals", ["last_activity_at"], unique=False)
    op.create_index(op.f("ix_deals_stage"), "deals", ["stage"], unique=False)

    op.create_table(
        "activities",
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("activity_type", sa.Enum("EMAIL", "CALL", "MEETING", name="activitytype"), nullable=False),
        sa.Column("direction", sa.Enum("INBOUND", "OUTBOUND", name="activitydirection"), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replied", sa.Boolean(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activities_deal_id"), "activities", ["deal_id"], unique=False)
    op.create_index(op.f("ix_activities_occurred_at"), "activities", ["occurred_at"], unique=False)

    op.create_table(
        "deal_analysis",
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.Enum("LOW", "MEDIUM", "HIGH", name="risklevel"), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("inactivity_days", sa.Integer(), nullable=False),
        sa.Column("interaction_count", sa.Integer(), nullable=False),
        sa.Column("no_reply", sa.Boolean(), nullable=False),
        sa.Column("churn_risk", sa.Boolean(), nullable=False),
        sa.Column("churn_reason", sa.String(length=255), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deal_analysis_deal_id"), "deal_analysis", ["deal_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_deal_analysis_deal_id"), table_name="deal_analysis")
    op.drop_table("deal_analysis")

    op.drop_index(op.f("ix_activities_occurred_at"), table_name="activities")
    op.drop_index(op.f("ix_activities_deal_id"), table_name="activities")
    op.drop_table("activities")

    op.drop_index(op.f("ix_deals_stage"), table_name="deals")
    op.drop_index(op.f("ix_deals_last_activity_at"), table_name="deals")
    op.drop_index(op.f("ix_deals_external_id"), table_name="deals")
    op.drop_index(op.f("ix_deals_contact_id"), table_name="deals")
    op.drop_table("deals")

    op.drop_index(op.f("ix_prospect_analysis_domain"), table_name="prospect_analysis")
    op.drop_index(op.f("ix_prospect_analysis_company_name"), table_name="prospect_analysis")
    op.drop_table("prospect_analysis")

    op.drop_index(op.f("ix_contacts_external_id"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_email"), table_name="contacts")
    op.drop_table("contacts")

    sa.Enum(name="risklevel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="activitydirection").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="activitytype").drop(op.get_bind(), checkfirst=True)
