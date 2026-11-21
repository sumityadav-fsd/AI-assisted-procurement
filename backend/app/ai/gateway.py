import hashlib, json, time
from pathlib import Path
from app.ai.providers import SarvamProvider
from app.core.config import AI_USE_CACHED_SAMPLES, AI_SAMPLES_DIR
from app.schemas.models import AITrace

class AIGateway:
    def __init__(self, provider=None):
        self.provider=provider or SarvamProvider()

    def _cache_file(self, step, prompt):
        key=hashlib.sha256((step+"|"+prompt).encode()).hexdigest()
        return AI_SAMPLES_DIR/f"{key}.json"

    @staticmethod
    def _write_cache(cache, result):
        # Cache is always under AI_SAMPLES_DIR (default: gitignored data_private/).
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            temporary=cache.with_suffix(".tmp")
            temporary.write_text(json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8")
            temporary.replace(cache)
        except OSError:
            # A read-only deployment may not be able to cache; provider output is still valid.
            return

    async def structured(self, step, prompt, schema, validator, deterministic):
        traces=[]
        cache=self._cache_file(step,prompt)
        messages=[{"role":"system","content":"Return only JSON matching the supplied schema. Never invent quantities, item codes, rates or commercial facts."},
                  {"role":"user","content":prompt}]
        started=time.monotonic()
        first_error=None
        raw=None
        try:
            raw=await self.provider.complete(messages,schema)
            try:
                result=validator(json.loads(raw))
                self._write_cache(cache,result)
                return result,[AITrace(step=step,provider="sarvam",model=self.provider.model,status="ok",attempt=1,
                    latency_ms=int((time.monotonic()-started)*1000))]
            except Exception as invalid:
                first_error=f"Invalid structured response: {invalid}"
        except Exception as exc:
            first_error=str(exc)

        # Exactly one repair/retry, whether the first response was invalid or the
        # first provider attempt failed transiently.
        repair_messages=list(messages)
        if raw is not None:
            repair_messages.extend([
                {"role":"assistant","content":raw},
                {"role":"user","content":f"Repair the JSON to satisfy the supplied schema. Validation error: {first_error}. Return JSON only."},
            ])
        else:
            repair_messages.insert(0,{"role":"system","content":"This is the single permitted retry. Return only JSON matching the schema; do not infer missing facts."})
        try:
            repaired=await self.provider.complete(repair_messages,schema)
            result=validator(json.loads(repaired))
            self._write_cache(cache,result)
            return result,[AITrace(step=step,provider="sarvam",model=self.provider.model,status="repaired",attempt=2,
                latency_ms=int((time.monotonic()-started)*1000),error=first_error[:200] if first_error else None)]
        except Exception as second:
            second_error=str(second)
            traces.append(AITrace(step=step,provider="sarvam",model=self.provider.model,status="failed",attempt=2,
                latency_ms=int((time.monotonic()-started)*1000),error=second_error[:200]))

        try:
            fallback=deterministic()
        except Exception as deterministic_error:
            fallback=None
            traces.append(AITrace(step=step,provider="deterministic-parser",status="failed",error=str(deterministic_error)[:200]))
        if fallback:
            return validator(fallback),traces+[AITrace(step=step,provider="deterministic-parser",status="fallback")]
        if AI_USE_CACHED_SAMPLES and cache.exists():
            return validator(json.loads(cache.read_text(encoding="utf-8"))),traces+[AITrace(step=step,provider="private-cache",status="cached")]
        raise RuntimeError(f"No valid AI, deterministic, or cached result for {step}: {second_error}")

    async def text(self, step, prompt, deterministic_text=None):
        started=time.monotonic()
        cache=self._cache_file(step,prompt)
        try:
            result=await self.provider.complete([{"role":"user","content":prompt}])
            self._write_cache(cache,{"text":result})
            return result,[AITrace(step=step,provider="sarvam",model=self.provider.model,status="ok",
                                   latency_ms=int((time.monotonic()-started)*1000))]
        except Exception as first:
            try:
                result=await self.provider.complete([{"role":"system","content":"Return a concise accurate response. Do not infer missing facts."},
                    {"role":"user","content":prompt},{"role":"assistant","content":""},
                    {"role":"user","content":f"Retry once. Previous provider error: {first}"}])
                self._write_cache(cache,{"text":result})
                return result,[AITrace(step=step,provider="sarvam",model=self.provider.model,status="repaired",attempt=2,
                                       latency_ms=int((time.monotonic()-started)*1000),error=str(first)[:200])]
            except Exception as second:
                traces=[AITrace(step=step,provider="sarvam",model=self.provider.model,status="failed",attempt=2,
                    latency_ms=int((time.monotonic()-started)*1000),error=str(second)[:200])]
                if deterministic_text:
                    return deterministic_text,traces+[AITrace(step=step,provider="deterministic-parser",status="fallback")]
                if AI_USE_CACHED_SAMPLES and cache.exists():
                    cached=json.loads(cache.read_text(encoding="utf-8"))
                    return cached.get("text"),traces+[AITrace(step=step,provider="private-cache",status="cached")]
                return None,traces
