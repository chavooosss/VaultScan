import asyncio
import logging
from providers import get_provider, PROVIDER_LABELS

logger = logging.getLogger("vaultscan.analyzer")

_NOTE_STRINGS = {
    "tr": {
        "synthesis_lang_prefix": "Dil",
        "not_participate": "(Not: {labels} bu analize katılamadı.)",
        "no_analysis": "Hiçbir AI analizi tamamlayamadı.",
        "failure_title": "⚠ Bazı modeller analize katılamadı",
        "failure_badge": "UYARI",
    },
    "en": {
        "synthesis_lang_prefix": "Language",
        "not_participate": "(Note: {labels} could not take part in this analysis.)",
        "no_analysis": "No AI completed the analysis.",
        "failure_title": "⚠ Some models could not take part in the analysis",
        "failure_badge": "WARNING",
    },
}

def _strings(lang: str) -> dict:
    return _NOTE_STRINGS.get(lang, _NOTE_STRINGS["tr"])

def analyze_code(code: str, language: str, provider: str, api_key: str, project_context: str = "", lang: str = "tr") -> str:
    return get_provider(provider).analyze_code(code, language, api_key, project_context, lang)

def analyze_multi(files: list, provider: str, api_key: str, project_context: str = "", lang: str = "tr") -> str:
    return get_provider(provider).analyze_multi(files, api_key, project_context, lang)

def _build_synthesis_input(per_provider_results: dict, language: str, failed: list, lang: str) -> str:
    s = _strings(lang)
    sections = "\n\n".join(
        f"### {PROVIDER_LABELS.get(name, name)} Analizi\n{html}"
        for name, html in per_provider_results.items()
    )
    note = ""
    if failed:
        failed_labels = ", ".join(PROVIDER_LABELS.get(p, p) for p in failed)
        note = "\n\n" + s["not_participate"].format(labels=failed_labels)
    return f"{s['synthesis_lang_prefix']}: {language}{note}\n\n{sections}"

def _failure_note_html(failed: list, errors: dict, lang: str) -> str:
    s = _strings(lang)
    items = "".join(
        f"<p><strong>{PROVIDER_LABELS.get(p, p)}:</strong> {errors[p]}</p>" for p in failed
    )
    return (
        '<div class="finding"><div class="finding-header">'
        f'<span class="finding-title">{s["failure_title"]}</span>'
        f'<span class="badge badge-info">{s["failure_badge"]}</span></div>'
        f'<div class="finding-body">{items}</div></div>'
    )

async def _run_collab(call_fn, providers: list, language: str, api_keys: dict, lang: str = "tr") -> str:
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
        raise RuntimeError(_strings(lang)["no_analysis"])

    if len(succeeded) == 1:
        result = next(iter(succeeded.values()))
        if failed:
            result = _failure_note_html(failed, {p: str(errors[p]) for p in failed}, lang) + result
        return result

    synthesizer = next(iter(succeeded))
    synthesis_input = _build_synthesis_input(succeeded, language, failed, lang)
    return await asyncio.to_thread(
        get_provider(synthesizer).synthesize, synthesis_input, api_keys[synthesizer], lang
    )

async def analyze_code_collab(code: str, language: str, providers: list, api_keys: dict, project_context: str = "", lang: str = "tr") -> str:
    return await _run_collab(lambda p: analyze_code(code, language, p, api_keys[p], project_context, lang), providers, language, api_keys, lang)

async def analyze_multi_collab(files: list, providers: list, api_keys: dict, project_context: str = "", lang: str = "tr") -> str:
    auto_label = "otomatik tespit" if lang == "tr" else "auto-detect"
    return await _run_collab(lambda p: analyze_multi(files, p, api_keys[p], project_context, lang), providers, auto_label, api_keys, lang)
