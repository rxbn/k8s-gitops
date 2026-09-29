"""Idempotently provision backup buckets and preserve node identity on the NAS."""
import hmac
import json
import pathlib
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path("/credentials")
TOKEN = (ROOT / "adminToken").read_text().strip()
CONFIG = json.loads((ROOT / "provision.json").read_text())


def api(operation, body=None, **query):
    url = "http://garage-backup-admin:3903/v2/" + operation
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


for attempt in range(60):
    try:
        status = api("GetClusterStatus")
        break
    except (urllib.error.URLError, TimeoutError):
        if attempt == 59:
            raise
        time.sleep(5)

layout = api("GetClusterLayout")
if layout["version"] == 0:
    nodes = [node for node in status["nodes"] if node["isUp"]]
    if len(nodes) != 1:
        raise RuntimeError("Initial provisioning requires exactly one live node")
    api("UpdateClusterLayout", {"roles": [{
        "id": nodes[0]["id"], "zone": "backup", "tags": [],
        "capacity": CONFIG["capacityBytes"],
    }]})
    api("ApplyClusterLayout", {"version": 1})

keys = {key["id"] for key in api("ListKeys")}
for key in CONFIG["keys"]:
    if key["accessKeyId"] not in keys:
        api("ImportKey", {name: key[name] for name in ("accessKeyId", "secretAccessKey", "name")})
    else:
        current = api("GetKeyInfo", id=key["accessKeyId"], showSecretKey="true")
        if not hmac.compare_digest(current["secretAccessKey"], key["secretAccessKey"]):
            raise RuntimeError("Existing credential differs from the declared configuration")

buckets = {alias: bucket["id"] for bucket in api("ListBuckets") for alias in bucket["globalAliases"]}
for bucket in CONFIG["buckets"]:
    if bucket not in buckets:
        buckets[bucket] = api("CreateBucket", {"globalAlias": bucket})["id"]
    for key in CONFIG["keys"]:
        if bucket in key["buckets"]:
            api("AllowBucketKey", {
                "bucketId": buckets[bucket], "accessKeyId": key["accessKeyId"],
                "permissions": {"read": True, "write": True, "owner": False},
            })

# Garage's automatic database snapshots do not include its node identity/layout.
identity = pathlib.Path("/mnt/data/recovery/identity")
identity.mkdir(parents=True, exist_ok=True)
for source in pathlib.Path("/mnt/meta").iterdir():
    if source.is_file() and not source.name.startswith("db."):
        temporary = identity / (source.name + ".tmp")
        shutil.copyfile(source, temporary)
        temporary.chmod(0o600)
        temporary.replace(identity / source.name)
print(f"Provisioned {len(buckets)} buckets; verified credentials; saved node identity", flush=True)
