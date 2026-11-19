"""LLM Client Factory supporting Google Gemini, Groq, OpenAI, Anthropic, and Ollama."""

import os
from typing import Any, Optional
from configs.settings import AppSettings, get_settings


def get_llm(settings: Optional[AppSettings] = None) -> Any:
    """Instantiate configured LangChain chat model based on AppSettings."""
    cfg = settings or get_settings()

    if cfg.llm_provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = cfg.google_api_key or cfg.llm_api_key or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError(
                    "Google API key not found. Please set GOOGLE_API_KEY in your .env file, "
                    "environment variables, or Streamlit Secrets (see deployment.md)."
                )
            model = cfg.llm_model_name if cfg.llm_model_name and cfg.llm_model_name != "gemini-2.5-flash" else "gemini-3.8-flash"
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=cfg.llm_temperature,
                max_output_tokens=cfg.llm_max_tokens,
            )
        except ImportError:
            raise ImportError(
                "langchain-google-genai is not installed. Please install it with: "
                "pip install langchain-google-genai"
            )

    elif cfg.llm_provider == "groq":
        try:
            from langchain_groq import ChatGroq
            api_key = cfg.groq_api_key or cfg.llm_api_key or os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError(
                    "Groq API key not found. Please set GROQ_API_KEY in your .env file, "
                    "environment variables, or Streamlit Secrets (see deployment.md)."
                )
            model = cfg.llm_model_name if cfg.llm_model_name and "gemini" not in cfg.llm_model_name else "llama-3.3-70b-versatile"
            return ChatGroq(
                model=model,
                groq_api_key=api_key,
                temperature=cfg.llm_temperature,
                max_tokens=cfg.llm_max_tokens,
            )
        except ImportError:
            raise ImportError(
                "langchain-groq is not installed. Please install it with: "
                "pip install langchain-groq"
            )

    elif cfg.llm_provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            api_key = cfg.openai_api_key or cfg.llm_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key not found. Please set OPENAI_API_KEY in your .env file, "
                    "environment variables, or Streamlit Secrets (see deployment.md)."
                )
            return ChatOpenAI(
                model=cfg.llm_model_name,
                api_key=api_key,
                temperature=cfg.llm_temperature,
                max_tokens=cfg.llm_max_tokens,
            )
        except ImportError:
            raise ImportError(
                "langchain-openai is not installed. Please install it with: "
                "pip install langchain-openai"
            )

    elif cfg.llm_provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=cfg.llm_model_name,
                api_key=cfg.llm_api_key,
                temperature=cfg.llm_temperature,
                max_tokens=cfg.llm_max_tokens,
            )
        except ImportError:
            raise ImportError(
                "langchain-anthropic is not installed. Please install it with: "
                "pip install langchain-anthropic"
            )

    elif cfg.llm_provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=cfg.llm_model_name,
                temperature=cfg.llm_temperature,
            )
        except ImportError:
            raise ImportError(
                "langchain-ollama is not installed. Please install it with: "
                "pip install langchain-ollama"
            )

    else:
        raise ValueError(f"Unsupported LLM provider: {cfg.llm_provider}")
