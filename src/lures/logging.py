"""Ініціалізація loguru — консоль + файл, перехоплення стандартного logging."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from .config import (
    DEFAULT_LOG_DIR_ENV,
    DEFAULT_LOG_LEVEL_CONSOLE_ENV,
    DEFAULT_LOG_LEVEL_FILE_ENV,
    LoggingConfig,
    load_logging_config,
)

if TYPE_CHECKING:
    from loguru import Logger


__all__ = ["InterceptHandler", "logger", "setup_logging"]


class InterceptHandler(logging.Handler):
    """Перехоплює записи стандартного logging і передає їх loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Отримуємо рівень loguru
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Знаходимо caller frame (перескакуємо logging internals)
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _resolve_log_dir(log_dir: str | None, configured_dir: str) -> Path:
    """Розв'язує шлях до папки логів.

    Пріоритет: явний аргумент (``--log-dir``) > ``LURES_LOG_DIR`` >
    ``config/logging.yaml`` > ``logs/``.
    """
    explicit = log_dir or os.environ.get(DEFAULT_LOG_DIR_ENV) or configured_dir
    return Path(explicit) if explicit else Path.cwd() / "logs"


def setup_logging(
    config: LoggingConfig | None = None,
    *,
    log_level: str | None = None,
    log_dir: str | None = None,
) -> Logger:
    """Налаштувати loguru згідно з конфігурацією.

    Args:
        config: Об'єкт LoggingConfig (якщо None — завантажується з config/logging.yaml)
        log_level: Перевизначити рівень для консолі (CLI --log-level)
        log_dir: Перевизначити папку для лог-файлів (CLI --log-dir)

    Рівні також можна задати через змінні середовища ``LURES_LOG_LEVEL_CONSOLE``
    та ``LURES_LOG_LEVEL_FILE``.

    Returns:
        Налаштований логер (loguru.logger)
    """
    if config is None:
        config = load_logging_config()

    # Видаляємо всі попередні handlers
    logger.remove()

    # Консольний handler
    if config.console.enabled:
        level = log_level or os.environ.get(DEFAULT_LOG_LEVEL_CONSOLE_ENV) or config.console.level
        logger.add(
            sys.stderr,
            level=level,
            format=config.console.format,
            colorize=config.console.colorize,
            backtrace=True,
            diagnose=True,
        )

    # Файловий handler
    if config.file.enabled:
        log_path = _resolve_log_dir(log_dir, config.file.dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_level = os.environ.get(DEFAULT_LOG_LEVEL_FILE_ENV) or config.file.level

        logger.add(
            log_path / "lures_{time:YYYY-MM-DD}.log",
            level=file_level,
            format=config.file.format,
            rotation=config.file.rotation,
            retention=config.file.retention,
            compression=config.file.compression,
            serialize=config.file.serialize,
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
        )

    # Перехоплення стандартного logging (sqlalchemy, uvicorn, etc.)
    if config.intercept_standard_logging:
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        # Встановлюємо рівень для конкретних шумних логерів
        for noisy_logger in ["sqlalchemy.engine", "httpx", "httpcore", "urllib3"]:
            logging.getLogger(noisy_logger).setLevel(config.intercept_level)

    logger.info(
        "Logging initialized (console={}, file={})",
        config.console.enabled,
        config.file.enabled,
    )
    return logger


# Експортуємо логер для зручного імпорту: from lures.logging import logger
# Це той самий синглтон loguru.logger, але після setup_logging() він буде налаштований.
