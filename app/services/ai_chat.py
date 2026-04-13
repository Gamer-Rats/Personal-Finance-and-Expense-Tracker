from __future__ import annotations

import httpx
from app.config import get_settings

try:
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    ADK_AVAILABLE = True
    ADK_IMPORT_ERROR = None
except Exception as exc:
    ADK_AVAILABLE = False
    ADK_IMPORT_ERROR = exc


class AIChatService:
    _app_name = "finance_tracker_chatbot"
    _system_instruction = (
        "You are a helpful AI assistant inside a Personal Finance and Expense Tracker web app. "
        "Answer clearly and briefly. Help users understand budgeting, subscriptions, spending, "
        "burn rate, savings, and how to use the app. "
        "Do not invent account-specific data that you cannot access. "
        "If a question needs personal financial advice, give general educational guidance only."
    )
    _session_service = None
    _runner = None
    _initialized_sessions: set[tuple[str, str]] = set()

    def __init__(self):
        self.settings = get_settings()

    def _normalize_api_base(self, base_url: str) -> str:
        base_url = (base_url or "").strip().rstrip("/")
        if not base_url:
            return ""
        if base_url.endswith("/v1"):
            return base_url
        return f"{base_url}/v1"

    def _chat_completion_endpoints(self) -> list[str]:
        base_url = (self.settings.ai_base_url or "").strip().rstrip("/")
        if not base_url:
            return []

        if base_url.endswith("/v1") or base_url.endswith("/api/v1"):
            candidates = [f"{base_url}/chat/completions"]
        elif base_url.endswith("/api"):
            candidates = [
                f"{base_url}/chat/completions",
                f"{base_url}/v1/chat/completions",
            ]
        else:
            candidates = [
                f"{base_url}/v1/chat/completions",
                f"{base_url}/api/chat/completions",
                f"{base_url}/api/v1/chat/completions",
            ]

        # Preserve order while removing duplicates.
        return list(dict.fromkeys(candidates))

    def _format_http_error(self, error: httpx.HTTPError) -> str:
        if isinstance(error, httpx.ConnectError):
            return (
                "The AI endpoint could not be reached. Check AI_BASE_URL and confirm the server is online."
            )

        if isinstance(error, httpx.TimeoutException):
            return (
                "The AI endpoint timed out. Please try again, or check if the model server is overloaded."
            )

        if isinstance(error, httpx.HTTPStatusError):
            response = error.response
            status_code = response.status_code
            detail = ""
            try:
                payload = response.json()
                detail = (
                    payload.get("detail")
                    or payload.get("message")
                    or payload.get("error")
                    or ""
                )
            except Exception:
                detail = (response.text or "").strip()

            detail_lower = str(detail).lower()
            if status_code in (401, 403):
                return "The AI endpoint rejected your API key. Check AI_API_KEY."
            if status_code == 404:
                return "The AI endpoint path was not found. Check AI_BASE_URL and endpoint compatibility."
            if "model not found" in detail_lower:
                return (
                    "The AI endpoint is reachable, but AI_MODEL_NAME was not found on that server. "
                    "Use a model id listed by your provider."
                )

            if self.settings.env.lower() != "production":
                snippet = str(detail)[:200] if detail else "No response detail"
                return f"AI endpoint error {status_code}: {snippet}"

        return (
            "Sorry, the assistant could not respond right now. Please try again in a moment."
        )

    def _build_agent(self) -> LlmAgent:
        api_base = self._normalize_api_base(self.settings.ai_base_url)
        model = LiteLlm(
            model=(self.settings.ai_model_name or "").strip(),
            api_base=api_base,
            api_key=(self.settings.ai_api_key or "").strip(),
        )

        return LlmAgent(
            model=model,
            name="finance_helper_agent",
            description="Answers finance tracker questions inside the app.",
            instruction=self.__class__._system_instruction,
        )

    def _ensure_runtime(self) -> None:
        if self.__class__._session_service is None:
            self.__class__._session_service = InMemorySessionService()

        if self.__class__._runner is None:
            self.__class__._runner = Runner(
                agent=self._build_agent(),
                app_name=self.__class__._app_name,
                session_service=self.__class__._session_service,
            )

    async def _ensure_session(self, user_id: str, session_id: str) -> None:
        key = (user_id, session_id)
        if key in self.__class__._initialized_sessions:
            return

        await self.__class__._session_service.create_session(
            app_name=self.__class__._app_name,
            user_id=user_id,
            session_id=session_id,
        )
        self.__class__._initialized_sessions.add(key)

    async def _ask_via_openai_api(self, question: str) -> str:
        api_key = (self.settings.ai_api_key or "").strip()
        model_name = (self.settings.ai_model_name or "").strip()
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": self.__class__._system_instruction},
                {"role": "user", "content": question},
            ],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        endpoints = self._chat_completion_endpoints()
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=45.0) as client:
            for endpoint in endpoints:
                try:
                    response = await client.post(endpoint, json=payload, headers=headers)
                    if response.status_code in (404, 405):
                        continue
                    response.raise_for_status()
                    body = response.json()
                    break
                except Exception as exc:
                    last_error = exc
            else:
                if last_error is not None:
                    raise last_error
                raise httpx.ConnectError("No valid AI completion endpoint candidates")

        choices = body.get("choices") or []
        if not choices:
            return "Sorry, I could not generate a response just now."

        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            combined = "".join(text_parts).strip()
            if combined:
                return combined

        return "Sorry, I could not generate a response just now."

    async def _ask_with_adk(self, username: str, question: str, session_id: str | None) -> str:
        self._ensure_runtime()
        user_id = username or "user"
        session_id = (session_id or f"chat-{user_id}").strip()
        await self._ensure_session(user_id=user_id, session_id=session_id)

        content = types.Content(
            role="user",
            parts=[types.Part(text=question)],
        )

        final_response = "Sorry, I could not generate a response just now."
        events = self.__class__._runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        )

        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text or final_response

        return final_response

    async def ask(self, username: str, question: str, session_id: str | None = None) -> str:
        question = (question or "").strip()
        if not question:
            return "Please type a question first."

        api_key = (self.settings.ai_api_key or "").strip()
        base_url = (self.settings.ai_base_url or "").strip()
        model_name = (self.settings.ai_model_name or "").strip()

        if not api_key or not base_url or not model_name:
            return (
                "The AI assistant is not configured yet. Add AI_API_KEY, AI_BASE_URL, and "
                "AI_MODEL_NAME to your .env file first."
            )

        try:
            if ADK_AVAILABLE:
                return await self._ask_with_adk(username, question, session_id)
            return await self._ask_via_openai_api(question)
        except httpx.HTTPError as error:
            return self._format_http_error(error)
        except Exception:
            try:
                return await self._ask_via_openai_api(question)
            except httpx.HTTPError as error:
                return self._format_http_error(error)
            except Exception:
                pass

            if not ADK_AVAILABLE and ADK_IMPORT_ERROR and self.settings.env.lower() != "production":
                return (
                    "Google ADK runtime could not be loaded, and fallback request failed. "
                    f"Import error: {type(ADK_IMPORT_ERROR).__name__}: {ADK_IMPORT_ERROR}"
                )

            return (
                "Sorry, the assistant could not respond right now. Please try again in a moment. "
                "If this keeps happening, check the AI settings in your .env file and confirm the model endpoint supports OpenAI-style chat calls."
            )
