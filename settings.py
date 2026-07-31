"""
Settings screen: configure fullscreen, language, and debug-by-default.

Settings are persisted to config/basic.json.
"""

import json
import os
import random
import pygame

from homepage import Button, HOME_BG_DIR, load_translations, t
from logger import log_event
from runtime import CONFIG_DIR, ensure_runtime_data

SETTINGS_PATH = os.path.join(CONFIG_DIR, "basic.json")
FONT_PATH = "fonts/LXGWWenKai-Regular.ttf"

DEFAULT_SETTINGS = {
    "fullscreen": False,
    "language": "zh",
    "debug_default": True,
}

# Colors
BG_COLOR = (30, 30, 30, 200)
BUTTON_COLOR = (50, 50, 50, 200)
BUTTON_HOVER = (70, 70, 70, 220)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (100, 200, 255)
ACTIVE_COLOR = (60, 120, 180, 230)

TOGGLE_WIDTH = 200
TOGGLE_HEIGHT = 44
LANG_BTN_WIDTH = 110
LANG_BTN_HEIGHT = 44


def load_settings():
    """Load settings from run/config/basic.json (falling back to defaults)."""
    ensure_runtime_data()
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(DEFAULT_SETTINGS)
    settings = dict(DEFAULT_SETTINGS)
    settings.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
    return settings


def save_settings(settings):
    """Persist settings to run/config/basic.json."""
    try:
        ensure_runtime_data()
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_event(f"Warning: failed to save settings: {e}")


def settings_screen(screen, screen_width, screen_height, settings):
    """
    Show the settings screen.
    Returns (settings, screen, screen_width, screen_height) on exit,
    or None if the window was closed.
    """
    clock = pygame.time.Clock()
    font_path = FONT_PATH
    if os.path.isfile(font_path):
        title_font = pygame.font.Font(font_path, 42)
        label_font = pygame.font.Font(font_path, 20)
        button_font = pygame.font.Font(font_path, 22)
    else:
        title_font = pygame.font.SysFont("Arial", 42)
        label_font = pygame.font.SysFont("Arial", 20)
        button_font = pygame.font.SysFont("Arial", 22)

    trans = load_translations()
    lang = settings["language"]

    # Random background
    bg_images = []
    if os.path.isdir(HOME_BG_DIR):
        for f in os.listdir(HOME_BG_DIR):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                try:
                    bg_images.append(pygame.image.load(os.path.join(HOME_BG_DIR, f)))
                except Exception:
                    pass
    bg_img = None
    if bg_images:
        bg_img = random.choice(bg_images)
    bg_scaled = (pygame.transform.scale(bg_img, (screen_width, screen_height))
                 if bg_img else None)

    pygame.mouse.set_visible(True)

    window_size = (screen_width, screen_height)
    running = True

    while running:
        clock.tick(60)

        center_x = screen_width // 2
        title_y = screen_height // 6
        row_gap = 76
        fs_y = title_y + 105
        lang_y = fs_y + row_gap
        dbg_y = lang_y + row_gap
        back_y = dbg_y + row_gap + 28

        # Keep labels and controls on the same row. This avoids overlap when
        # translated labels have different widths or font metrics.
        control_x = center_x + 20
        label_center_x = center_x - 120

        on_text = t(trans, "settings_on", lang)
        off_text = t(trans, "settings_off", lang)

        fs_btn = Button(control_x, fs_y,
                        TOGGLE_WIDTH, TOGGLE_HEIGHT,
                        on_text if settings["fullscreen"] else off_text, button_font)
        fs_btn.color = ACTIVE_COLOR if settings["fullscreen"] else BUTTON_COLOR

        dbg_btn = Button(control_x, dbg_y,
                         TOGGLE_WIDTH, TOGGLE_HEIGHT,
                         on_text if settings["debug_default"] else off_text, button_font)
        dbg_btn.color = ACTIVE_COLOR if settings["debug_default"] else BUTTON_COLOR

        lang_zh = Button(control_x, lang_y,
                         LANG_BTN_WIDTH, LANG_BTN_HEIGHT, "中文", button_font)
        lang_en = Button(control_x + LANG_BTN_WIDTH + 10, lang_y,
                         LANG_BTN_WIDTH, LANG_BTN_HEIGHT, "English", button_font)
        lang_zh.color = ACTIVE_COLOR if lang == "zh" else BUTTON_COLOR
        lang_en.color = ACTIVE_COLOR if lang == "en" else BUTTON_COLOR

        back_btn = Button(center_x - TOGGLE_WIDTH // 2, back_y,
                          TOGGLE_WIDTH, TOGGLE_HEIGHT,
                          t(trans, "settings_back", lang), button_font)

        # Buttons are rebuilt after resize and setting changes. Recalculate
        # hover from the current cursor position so a stationary cursor does
        # not lose its hover state between frames.
        mouse_pos = pygame.mouse.get_pos()
        for btn in (fs_btn, lang_zh, lang_en, dbg_btn, back_btn):
            btn.hover = btn.rect.collidepoint(mouse_pos)

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.VIDEORESIZE and not settings["fullscreen"]:
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode(
                    (screen_width, screen_height), pygame.RESIZABLE
                )
                if bg_img:
                    bg_scaled = pygame.transform.scale(bg_img,
                                                       (screen_width, screen_height))

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if fs_btn.handle_event(event):
                    settings["fullscreen"] = not settings["fullscreen"]
                    if settings["fullscreen"]:
                        window_size = (screen_width, screen_height)
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        screen_width, screen_height = window_size
                        screen = pygame.display.set_mode(
                            (screen_width, screen_height), pygame.RESIZABLE
                        )
                    screen_width, screen_height = screen.get_size()
                    if bg_img:
                        bg_scaled = pygame.transform.scale(
                            bg_img, (screen_width, screen_height))
                    save_settings(settings)
                elif lang_zh.handle_event(event):
                    lang = "zh"
                    settings["language"] = lang
                    save_settings(settings)
                elif lang_en.handle_event(event):
                    lang = "en"
                    settings["language"] = lang
                    save_settings(settings)
                elif dbg_btn.handle_event(event):
                    settings["debug_default"] = not settings["debug_default"]
                    save_settings(settings)
                elif back_btn.handle_event(event):
                    running = False

            elif event.type == pygame.MOUSEMOTION:
                for btn in (fs_btn, lang_zh, lang_en, dbg_btn, back_btn):
                    btn.handle_event(event)

        # RENDER
        if bg_scaled:
            screen.blit(bg_scaled, (0, 0))
        else:
            screen.fill((20, 20, 30))

        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill(BG_COLOR)
        screen.blit(overlay, (0, 0))

        title_text = t(trans, "settings_title", lang)
        title_surf = title_font.render(title_text, True, ACCENT_COLOR)
        title_shadow = title_font.render(title_text, True, (0, 0, 0))
        title_rect = title_surf.get_rect(center=(center_x, title_y))
        screen.blit(title_shadow, (title_rect.x + 2, title_rect.y + 2))
        screen.blit(title_surf, title_rect)

        def draw_label(text, y):
            lbl = label_font.render(text, True, TEXT_COLOR)
            screen.blit(lbl, lbl.get_rect(midright=(label_center_x, y + TOGGLE_HEIGHT // 2)))

        draw_label(t(trans, "settings_fullscreen", lang), fs_y)
        draw_label(t(trans, "settings_language", lang), lang_y)
        draw_label(t(trans, "settings_debug_default", lang), dbg_y)

        fs_btn.draw(screen)
        lang_zh.draw(screen)
        lang_en.draw(screen)
        dbg_btn.draw(screen)
        back_btn.draw(screen)

        pygame.display.flip()

    return settings, screen, screen_width, screen_height
