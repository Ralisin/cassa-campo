import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException, status

from app.core.config import settings


@dataclass(frozen=True)
class ReceiptStorage:
    base_url: str
    service_role_key: str
    bucket: str

    def upload(self, storage_key: str, content: bytes, content_type: str) -> None:
        self._request(
            "POST",
            f"/object/{self.bucket}/{self._quote_path(storage_key)}",
            body=content,
            headers={"Content-Type": content_type, "x-upsert": "false"},
        )

    def signed_url(self, storage_key: str, expires_in: int = 300) -> str:
        response = self._request(
            "POST",
            f"/object/sign/{self.bucket}/{self._quote_path(storage_key)}",
            body=json.dumps({"expiresIn": expires_in}).encode(),
            headers={"Content-Type": "application/json"},
        )
        payload = json.loads(response.decode())
        signed_url = payload.get("signedURL") or payload.get("signedUrl")
        if not signed_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Storage did not return a signed URL",
            )
        if signed_url.startswith("http"):
            return signed_url
        return f"{self.base_url.rstrip('/')}/storage/v1{signed_url}"

    def delete(self, storage_key: str) -> None:
        self._request(
            "DELETE",
            f"/object/{self.bucket}/{self._quote_path(storage_key)}",
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        request = Request(
            f"{self.base_url.rstrip('/')}/storage/v1{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key,
                **(headers or {}),
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                return response.read()
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace") or exc.reason
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Storage request failed: {detail}",
            ) from exc
        except URLError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Storage service is unreachable",
            ) from exc

    @staticmethod
    def _quote_path(path: str) -> str:
        return "/".join(quote(part, safe="") for part in path.split("/"))


def get_receipt_storage() -> ReceiptStorage:
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Receipt storage is not configured",
        )
    return ReceiptStorage(
        base_url=settings.supabase_url,
        service_role_key=settings.supabase_secret_key,
        bucket=settings.supabase_storage_bucket,
    )
