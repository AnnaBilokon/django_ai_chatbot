# chat/views.py
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from dotenv import load_dotenv
import os, requests

load_dotenv()

# Default is OpenAI; can be overridden per-session via the dropdown
DEFAULT_PROVIDER = os.getenv("PROVIDER", "openai").lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Lazy import: only when we actually call OpenAI
def _get_openai_client():
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_MSG = {
    "role": "system",
    "content": "You are a helpful, concise assistant. Keep answers short unless asked."
}

def _history(request):
    if "history" not in request.session:
        request.session["history"] = [SYSTEM_MSG]
    return request.session["history"]

def _append(request, role, content):
    h = _history(request)
    h.append({"role": role, "content": content})
    request.session["history"] = h
    request.session.modified = True

def _get_provider(request) -> str:
    # session override, else project default
    return (request.session.get("provider") or DEFAULT_PROVIDER).lower()

def _set_provider(request, provider: str):
    provider = provider.lower()
    if provider not in ("openai", "ollama"):
        raise ValueError("Invalid provider")
    request.session["provider"] = provider
    request.session.modified = True

def _to_ollama_messages(history):
    return [{"role": m["role"], "content": m["content"]} for m in history]

def _ask(history, provider: str) -> str:
    if provider == "openai":
        client = _get_openai_client()
        resp = client.responses.create(
            model="gpt-4o-mini",
            input=history
        )
        return getattr(resp, "output_text", "").strip()
    else:  # ollama
        payload = {
            "model": OLLAMA_MODEL,
            "messages": _to_ollama_messages(history),
            "stream": False
        }
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        return (data.get("message", {}) or {}).get("content", "").strip()

@csrf_protect
def chat_view(request):
    _ = _history(request)
    provider = _get_provider(request)

    if request.method == "POST":
        user_text = request.POST.get("message", "").strip()
        if user_text:
            _append(request, "user", user_text)
            try:
                assistant_text = _ask(request.session["history"], provider)
            except Exception as e:
                assistant_text = f"(Error calling {provider}: {e})"
            _append(request, "assistant", assistant_text)
        return redirect("chat")

    display_msgs = [m for m in request.session["history"] if m["role"] != "system"]
    return render(request, "chat.html", {"messages": display_msgs, "provider": provider})

@require_POST
@csrf_protect
def set_provider_view(request):
    chosen = request.POST.get("provider", "").lower()
    try:
        _set_provider(request, chosen)
    except Exception:
        pass  # ignore invalid values
    return redirect("chat")

def reset_view(request):
    request.session.pop("history", None)
    return redirect("chat")
