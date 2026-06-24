import asyncio
import logging
from providers import get_provider, PROVIDER_LABELS

logger = logging.getLogger("vaultscan.analyzer")

def analyze_code(code: str, language: str, provider: str, api_key: str) -> str:
    return get_provider(provider).analyze_code(code, language, api_key)

def analyze_multi(files: list, provider: str, api_key: str) -> str:
    return get_provider(provider).analyze_multi(files, api_key)

def _build_synthesis_input(per_provider_results: dict, language: str, failed: list) -> str:
    sections = "\n\n".join(
        f"### {PROVIDER_LABELS.get(name, name)} Analizi\n{html}"
        for name, html in per_provider_results.items()
    )
    note = ""
    if failed:
        failed_labels = ", ".join(PROVIDER_LABELS.get(p, p) for p in failed)
        note = f"\n\n(Not: {failed_labels} bu analize katılamadı.)"
    return f"Dil: {language}{note}\n\n{sections}"

def _failure_note_html(failed: list, errors: dict) -> str:
    items = "".join(
        f"<p><strong>{PROVIDER_LABELS.get(p, p)}:</strong> {errors[p]}</p>" for p in failed
    )
    return (
        '<div class="finding"><div class="finding-header">'
        '<span class="finding-title">⚠ Bazı modeller analize katılamadı</span>'
        '<span class="badge badge-info">UYARI</span></div>'
        f'<div class="finding-body">{items}</div></div>'
    )

async def _run_collab(call_fn, providers: list, language: str, api_keys: dict) -> str:
    if len(providers) == 1:
        return await asyncio.to_thread(call_fn, providers[0])

    raw_results = await asyncio.gather(
        *(asyncio.to_thread(call_fn, p) for p in providers),
        return_exceptions=True,
    )

    succeeded = {p: r for p, r in zip(providers, raw_results) if not isinstance(r, Exception)}
    failed = [p for p, r in zip(providers, raw_results) if isinstance(r, Exception)]
    errors = {p: r for p, r in zip(providers, raw_results) if isinstance(r, Exception)}

    for p, err in errors.items():
        logger.error("Provider %s collab analizinde başarısız: %r", p, err)

    if not succeeded:
        raise RuntimeError("Hiçbir AI analizi tamamlayamadı.")

    if len(succeeded) == 1:
        result = next(iter(succeeded.values()))
        if failed:
            result = _failure_note_html(failed, {p: str(errors[p]) for p in failed}) + result
        return result

    synthesizer = next(iter(succeeded))
    synthesis_input = _build_synthesis_input(succeeded, language, failed)
    return await asyncio.to_thread(
        get_provider(synthesizer).synthesize, synthesis_input, api_keys[synthesizer]
    )

async def analyze_code_collab(code: str, language: str, providers: list, api_keys: dict) -> str:
    return await _run_collab(lambda p: analyze_code(code, language, p, api_keys[p]), providers, language, api_keys)

async def analyze_multi_collab(files: list, providers: list, api_keys: dict) -> str:
    return await _run_collab(lambda p: analyze_multi(files, p, api_keys[p]), providers, "otomatik tespit", api_keys)
