#!/usr/bin/env python3
"""Copy S3 buckets without deleting data; verify transferred bytes with SHA-256.

Requires boto3 and /credentials/migration.json containing source/destination
endpoint, accessKeyId, secretAccessKey, region and a buckets list. Run with
--verify to read/compare every object, or --inventory for a source summary.
Credentials and object names are never logged. Existing equal single-part
ETags/sizes are skipped during incremental copy; use --verify for full checks.
"""
import concurrent.futures
import hashlib
import gzip
import json
import sys
import time

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config

configuration = json.load(open("/credentials/migration.json"))


def client(settings):
    return boto3.client(
        "s3", endpoint_url=settings["endpoint"],
        aws_access_key_id=settings["accessKeyId"],
        aws_secret_access_key=settings["secretAccessKey"],
        region_name=settings.get("region", "us-east-1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      retries={"max_attempts": 8, "mode": "standard"},
                      connect_timeout=10, read_timeout=900,
                      max_pool_connections=16, request_checksum_calculation="when_required",
                      response_checksum_validation="when_required"),
    )


source, destination = (client(configuration[name]) for name in ("source", "destination"))
transfer = TransferConfig(multipart_threshold=32 * 1024**2, multipart_chunksize=16 * 1024**2,
                          max_concurrency=2, use_threads=False)


def objects(connection, bucket):
    manifest = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--source-manifest=")), None)
    if manifest and connection is source:
        with gzip.open(manifest, "rt") as handle:
            yield from json.load(handle)
        return
    prefixes = next((arg.split("=", 1)[1].split(",") for arg in sys.argv if arg.startswith("--prefixes=")), [""])
    current_versions = connection is source and "--version-listing" in sys.argv
    prefix_file = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--prefix-file=")), None)
    if prefix_file and connection is source:
        prefixes = json.load(open(prefix_file))
        def listing(prefix):
            return [item for page in connection.get_paginator("list_object_versions").paginate(Bucket=bucket, Prefix=prefix) for item in page.get("Versions", []) if item["IsLatest"]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for future in concurrent.futures.as_completed([executor.submit(listing, prefix) for prefix in prefixes]):
                yield from future.result()
        return
    for prefix in prefixes:
        operation = "list_object_versions" if current_versions else "list_objects_v2"
        for page in connection.get_paginator(operation).paginate(Bucket=bucket, Prefix=prefix):
            if current_versions:
                yield from (item for item in page.get("Versions", []) if item["IsLatest"])
            else:
                yield from page.get("Contents", [])


def digest_body(body):
    digest = hashlib.sha256()
    try:
        for block in iter(lambda: body.read(1024**2), b""):
            digest.update(block)
    finally:
        body.close()
    return digest.digest()


class HashedReader:
    def __init__(self, body):
        self.body = body
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        block = self.body.read(size)
        self.digest.update(block)
        return block


def copy_object(bucket, item, existing, verify):
    key = item["Key"]
    previous = existing.get(key)
    equal = previous and previous["Size"] == item["Size"] and previous["ETag"] == item["ETag"]
    if not verify and equal and "-" not in item["ETag"]:
        return "unchanged", item["Size"]
    if verify:
        if not previous or previous["Size"] != item["Size"]:
            raise RuntimeError("Missing object or size mismatch")
        left = digest_body(source.get_object(Bucket=bucket, Key=key)["Body"])
    else:
        version = {"VersionId": item["VersionId"]} if "VersionId" in item else {}
        response = source.get_object(Bucket=bucket, Key=key, IfMatch=item["ETag"], **version)
        reader = HashedReader(response["Body"])
        attributes = {name: response[name] for name in (
            "ContentType", "ContentEncoding", "ContentDisposition", "ContentLanguage",
            "CacheControl", "Expires", "Metadata") if name in response}
        try:
            destination.upload_fileobj(reader, bucket, key, ExtraArgs=attributes, Config=transfer)
        finally:
            response["Body"].close()
        left = reader.digest.digest()
    right = digest_body(destination.get_object(Bucket=bucket, Key=key)["Body"])
    if left != right:
        raise RuntimeError("SHA-256 content mismatch")
    return "verified" if verify else "copied-and-verified", item["Size"]


def run_bucket(bucket):
    started = time.monotonic()
    counts = {}
    size = 0
    if "--inventory" in sys.argv:
        for item in objects(source, bucket):
            counts["objects"] = counts.get("objects", 0) + 1
            size += item["Size"]
    else:
        versioning = source.get_bucket_versioning(Bucket=bucket)
        if versioning.get("Status") in ("Enabled", "Suspended") and "--current-versions" not in sys.argv:
            raise RuntimeError("Versioned bucket needs a separate version-preserving migration")
        existing = {item["Key"]: item for item in objects(destination, bucket)}
        print(json.dumps({"bucket": bucket, "destinationObjects": len(existing), "phase": "start"}), flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            pending = set()
            for item in objects(source, bucket):
                pending.add(executor.submit(copy_object, bucket, item, existing, "--verify" in sys.argv))
                if len(pending) >= 32:
                    done, pending = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
                    for result in done:
                        action, length = result.result()
                        counts[action] = counts.get(action, 0) + 1
                        size += length
                    if sum(counts.values()) % 250 < 8:
                        print(json.dumps({"bucket": bucket, "counts": counts, "bytes": size, "phase": "progress"}), flush=True)
            for result in concurrent.futures.as_completed(pending):
                action, length = result.result()
                counts[action] = counts.get(action, 0) + 1
                size += length
    print(json.dumps({"bucket": bucket, "counts": counts, "bytes": size,
                      "seconds": round(time.monotonic() - started), "phase": "complete"}), flush=True)


selected = next((arg.split("=", 1)[1].split(",") for arg in sys.argv if arg.startswith("--buckets=")), configuration["buckets"])
for bucket in selected:
    if bucket not in configuration["buckets"]:
        raise RuntimeError("Bucket is outside the configured migration scope")
    run_bucket(bucket)
