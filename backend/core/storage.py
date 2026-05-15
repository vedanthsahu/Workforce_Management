"""
S3 storage helpers for floor layout uploads.
"""

from __future__ import annotations

import uuid

import boto3
from botocore.client import BaseClient
from fastapi import HTTPException, UploadFile, status

from backend.core.config import get_settings

settings = get_settings()


def get_s3_client() -> BaseClient:
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def validate_svg_file(file: UploadFile) -> None:
    filename = (file.filename or "").lower()

    if not filename.endswith(".svg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_file_type",
                "message": "Only SVG files are allowed.",
            },
        )

    if file.content_type not in {
        "image/svg+xml",
        "application/svg+xml",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_content_type",
                "message": "Invalid SVG content type.",
            },
        )


def build_layout_object_key(
    *,
    tenant_id: str,
    site_id: str,
    building_id: str,
    floor_id: str,
) -> str:
    unique_id = uuid.uuid4().hex

    return (
        f"tenant_{tenant_id}/"
        f"site_{site_id}/"
        f"building_{building_id}/"
        f"floor_{floor_id}/"
        f"layouts/temp/"
        f"{unique_id}.svg"
    )


def upload_svg_to_s3(
    *,
    file: UploadFile,
    tenant_id: str,
    site_id: str,
    building_id: str,
    floor_id: str,
) -> str:
    validate_svg_file(file)

    object_key = build_layout_object_key(
        tenant_id=tenant_id,
        site_id=site_id,
        building_id=building_id,
        floor_id=floor_id,
    )

    s3_client = get_s3_client()

    s3_client.upload_fileobj(
        Fileobj=file.file,
        Bucket=settings.aws_s3_bucket_name,
        Key=object_key,
        ExtraArgs={
            "ContentType": "image/svg+xml",
        },
    )

    return f"{settings.aws_s3_public_base_url}/{object_key}"