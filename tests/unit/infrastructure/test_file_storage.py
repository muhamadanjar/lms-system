import stat

from app.config.file_storage import FileStorageSettings
from app.infrastructure.storage.file_storage import ConfiguredFileStorage, S3CompatibleFileStorage


async def test_local_storage_round_trips_private_bytes(tmp_path):
    storage = ConfiguredFileStorage(FileStorageSettings(local_root=str(tmp_path)))
    await storage.put("a1b2c3", b"private evidence", "text/plain")

    assert await storage.get("local", "a1b2c3") == b"private evidence"
    assert (tmp_path / "a1" / "a1b2c3").exists()
    assert stat.S_IMODE((tmp_path / "a1" / "a1b2c3").stat().st_mode) == 0o600
    await storage.delete("local", "a1b2c3")
    assert not (tmp_path / "a1" / "a1b2c3").exists()


def test_s3_compatible_adapter_creates_client_from_configuration(monkeypatch):
    settings = FileStorageSettings(backend="s3", bucket="private-bucket", endpoint_url="http://storage.test")
    storage = S3CompatibleFileStorage(settings)

    captured = {}
    client = object()

    def fake_client(service, **kwargs):
        captured["service"] = service
        captured.update(kwargs)
        return client

    import boto3

    monkeypatch.setattr(boto3, "client", fake_client)
    assert storage._get_client() is client
    assert captured["service"] == "s3"
    assert captured["endpoint_url"] == "http://storage.test"
    assert captured["region_name"] == "us-east-1"
    assert captured["config"].connect_timeout == 5
import stat
