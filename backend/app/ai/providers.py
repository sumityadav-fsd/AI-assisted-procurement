import json, io, time, zipfile
import httpx
from app.core.config import SARVAM_API_KEY, SARVAM_CHAT_URL, SARVAM_MODEL, AI_TIMEOUT_SECONDS

class ProviderError(RuntimeError):
    pass

class SarvamProvider:
    name = "sarvam"
    model = SARVAM_MODEL

    @staticmethod
    def extract_content(body: dict) -> str:
        return body["choices"][0]["message"]["content"]

    async def complete(self, messages: list[dict], schema: dict | None = None) -> str:
        if not SARVAM_API_KEY:
            raise ProviderError("SARVAM_API_KEY is not configured")
        payload = {"model": self.model, "messages": messages, "temperature": 0.1, "max_tokens": 1800}
        if schema:
            payload["response_format"] = {"type":"json_schema","json_schema":{
                "name":"procurement_output","strict":True,"schema":schema
            }}
        headers = {"api-subscription-key": SARVAM_API_KEY, "Content-Type":"application/json"}
        async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
            response = await client.post(SARVAM_CHAT_URL, headers=headers, json=payload)
            if response.is_error:
                raise ProviderError(f"Sarvam HTTP {response.status_code}: {response.text[:500]}")
            body = response.json()
        try:
            return self.extract_content(body)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Sarvam response did not contain choices[0].message.content") from exc

    async def parse_document(self, document_bytes: bytes, filename: str, mime_type: str = "application/pdf") -> str:
        """Run Sarvam Document AI Parse and return page-labelled extracted text.

        Uses the documented asynchronous job flow: multipart POST, status polling,
        then download-url + ZIP output. No endpoint paths are inferred.
        """
        if not SARVAM_API_KEY:
            raise ProviderError("SARVAM_API_KEY is not configured")
        headers = {"api-subscription-key": SARVAM_API_KEY}
        timeout = httpx.Timeout(AI_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.sarvam.ai/doc-ai/v1/job/parse",
                headers=headers,
                data={"language": "en-IN", "output_format": "json", "content_type": "printed"},
                files={"file": (filename, document_bytes, mime_type)},
            )
            if response.is_error:
                raise ProviderError(f"Sarvam Document AI submit HTTP {response.status_code}: {response.text[:400]}")
            job = response.json()
            job_id = job.get("job_id")
            if not job_id:
                raise ProviderError("Sarvam Document AI response did not contain job_id")

            terminal = {"completed", "partially_completed", "failed", "rejected"}
            status = str(job.get("status", "pending")).lower()
            deadline = time.monotonic() + min(AI_TIMEOUT_SECONDS, 28.0)
            while status not in terminal and time.monotonic() < deadline:
                await __import__("asyncio").sleep(1.0)
                poll = await client.get(
                    f"https://api.sarvam.ai/doc-ai/v1/job/{job_id}/status", headers=headers
                )
                if poll.is_error:
                    raise ProviderError(f"Sarvam Document AI status HTTP {poll.status_code}: {poll.text[:300]}")
                status = str(poll.json().get("status", "")).lower()
            if status not in {"completed", "partially_completed"}:
                raise ProviderError(f"Sarvam Document AI job ended with status {status or 'timeout'}")

            link = await client.get(
                f"https://api.sarvam.ai/doc-ai/v1/job/{job_id}/download-url", headers=headers
            )
            if link.is_error:
                raise ProviderError(f"Sarvam Document AI download URL HTTP {link.status_code}: {link.text[:300]}")
            download = link.json()
            method = str(download.get("method", "GET")).upper()
            url = download.get("url")
            if method != "GET" or not url:
                raise ProviderError("Sarvam Document AI returned an unsupported download method or missing URL")
            file_response = await client.get(url, headers=download.get("headers") or {})
            if file_response.is_error:
                raise ProviderError(f"Sarvam Document AI output download HTTP {file_response.status_code}")

        try:
            with zipfile.ZipFile(io.BytesIO(file_response.content)) as archive:
                page_files = sorted(
                    (name for name in archive.namelist() if "/metadata/page_" in name and name.endswith(".json")),
                    key=lambda name: name,
                )
                pages = []
                for index, name in enumerate(page_files, 1):
                    try:
                        payload = json.loads(archive.read(name).decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    texts = []
                    def collect(value):
                        if isinstance(value, dict):
                            if isinstance(value.get("text"), str):
                                texts.append(value["text"])
                            for key, child in value.items():
                                if key != "text": collect(child)
                        elif isinstance(value, list):
                            for child in value: collect(child)
                    collect(payload)
                    page_text = "\n".join(x.strip() for x in texts if x.strip())
                    if page_text:
                        page_number = index
                        import re
                        match = re.search(r"page_(\d+)", name)
                        if match: page_number = int(match.group(1))
                        pages.append(f"[PAGE {page_number}]\n{page_text}")
                if pages:
                    return "\n".join(pages)
                markdown = next((n for n in archive.namelist() if n.lower().endswith((".md", ".txt", ".html"))), None)
                if markdown:
                    content = archive.read(markdown).decode("utf-8", errors="replace")
                    return "[PAGE 1]\n" + content
        except (zipfile.BadZipFile, OSError) as exc:
            raise ProviderError("Sarvam Document AI output was not a readable ZIP") from exc
        raise ProviderError("Sarvam Document AI output ZIP contained no readable page text")

    async def translate_note(self, text: str, language: str) -> str:
        prompt = f"Summarise this procurement note in English. Preserve all quantities, units, dates and names exactly. Source language: {language}. Do not infer missing facts. Return only the summary.\n\n{text}"
        return await self.complete([{"role":"user","content":prompt}])
