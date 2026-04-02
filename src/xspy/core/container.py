"""Dependency injection container — the wiring diagram of the entire application."""

from __future__ import annotations

from dependency_injector import containers, providers

from xspy.core.config import XspySettings, load_llm_models, load_settings
from xspy.core.llm.client import ModelConfig
from xspy.core.llm.prompts import PromptManager
from xspy.core.llm.router import ModelRouter


def _build_model_router(settings: XspySettings) -> ModelRouter:
    llm_data = load_llm_models(settings)
    configs = [ModelConfig(**m) for m in llm_data.get("models", [])]
    return ModelRouter(configs, llm_data.get("task_routing", {}))


class ApplicationContainer(containers.DeclarativeContainer):
    """Top-level DI container for xspy."""

    wiring_config = containers.WiringConfiguration(
        packages=["xspy.web"],
    )

    # --- Configuration ---
    settings = providers.Singleton(load_settings)

    # --- LLM Layer ---
    model_router = providers.Singleton(_build_model_router, settings=settings)
    prompt_manager = providers.Singleton(PromptManager)

    # --- Parser ---
    novel_parser = providers.Singleton(
        "xspy.parser.service.NovelParserService",
    )

    # --- Agents ---
    screenwriter = providers.Singleton(
        "xspy.agent.service.ScreenwriterService",
        router=model_router,
        prompts=prompt_manager,
    )
    character_engine = providers.Singleton(
        "xspy.character.service.CharacterEngineService",
        router=model_router,
        prompts=prompt_manager,
    )

    # --- Emotion ---
    emotion_system = providers.Singleton(
        "xspy.emotion.service.EmotionService",
        router=model_router,
        prompts=prompt_manager,
    )

    # --- Voice Bank ---
    voice_bank = providers.Singleton(
        "xspy.voice.service.VoiceBankService",
    )

    # --- TTS ---
    tts_client = providers.Singleton(
        "xspy.tts.service.TTSClientService",
        base_url=providers.Callable(lambda s: s.tts.base_url, settings),
        timeout=providers.Callable(lambda s: s.tts.timeout_seconds, settings),
        max_retries=providers.Callable(lambda s: s.tts.max_retries, settings),
    )

    # --- Audio ---
    audio_processor = providers.Singleton(
        "xspy.audio.service.AudioProcessorService",
        output_dir=providers.Callable(lambda s: s.pipeline.output_dir, settings),
    )

    # --- Pipeline ---
    pipeline = providers.Singleton(
        "xspy.pipeline.service.PipelineOrchestrator",
        settings=settings,
        parser=novel_parser,
        screenwriter=screenwriter,
        character_engine=character_engine,
        emotion_system=emotion_system,
        voice_bank=voice_bank,
        tts_client=tts_client,
        audio_processor=audio_processor,
    )
