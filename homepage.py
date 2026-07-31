"""
Homepage (main menu) for My2DWorld.
Displays random background, language toggle, login/register UI.
"""

import json
import os
import random
import pygame

from account import register, login, init_default_account

# Paths
HOME_BG_DIR = "image/Homepage_background"
TRANSLATE_PATH = "translate/translate.json"
FONT_PATH = "fonts/LXGWWenKai-Regular.ttf"

# Colors
BG_COLOR = (30, 30, 30, 180)
BUTTON_COLOR = (50, 50, 50, 200)
BUTTON_HOVER = (70, 70, 70, 220)
INPUT_COLOR = (40, 40, 40, 200)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (100, 200, 255)
ERROR_COLOR = (255, 100, 100)
SUCCESS_COLOR = (100, 255, 100)

BUTTON_WIDTH = 260
BUTTON_HEIGHT = 50
INPUT_WIDTH = 260
INPUT_HEIGHT = 40

# Default account
DEFAULT_USER = "steve"
DEFAULT_PASS = "1234asdf"


class TextInput:
    """A simple text input field."""

    def __init__(self, x, y, width, height, font, is_password=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.is_password = is_password
        self.text = ""
        self.active = False
        self.cursor_visible = True
        self.last_blink = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                if event.unicode.isprintable() and len(self.text) < 32:
                    self.text += event.unicode
        return None

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_blink > 500:
            self.cursor_visible = not self.cursor_visible
            self.last_blink = now

    def draw(self, screen):
        pygame.draw.rect(screen, INPUT_COLOR, self.rect, border_radius=4)
        pygame.draw.rect(screen, ACCENT_COLOR if self.active else (100, 100, 100),
                         self.rect, 2, border_radius=4)
        display_text = self.text
        if self.is_password:
            display_text = "*" * len(self.text)
        text_surf = self.font.render(display_text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 8, self.rect.centery))
        screen.blit(text_surf, text_rect)
        if self.active and self.cursor_visible:
            cursor_x = text_rect.right + 2
            pygame.draw.line(screen, TEXT_COLOR,
                             (cursor_x, self.rect.y + 6),
                             (cursor_x, self.rect.bottom - 6), 2)


class Button:
    """A simple clickable button."""

    def __init__(self, x, y, width, height, text, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def set_text(self, text):
        self.text = text

    def draw(self, screen):
        color = BUTTON_HOVER if self.hover else BUTTON_COLOR
        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        pygame.draw.rect(screen, ACCENT_COLOR, self.rect, 2, border_radius=6)
        text_surf = self.font.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


def load_translations():
    try:
        with open(TRANSLATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: failed to load translations: {e}")
        return {"language": "zh", "gui": {}, "blocks": {}}


def t(translate_data, key, lang, **kwargs):
    texts = translate_data.get("gui", {}).get(key, {})
    text = texts.get(lang, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


def homepage(screen, screen_width, screen_height):
    """
    Show the homepage/menu.
    Returns (username, lang, settings, screen_width, screen_height),
    or None if quitting.
    """
    clock = pygame.time.Clock()
    if os.path.isfile(FONT_PATH):
        title_font = pygame.font.Font(FONT_PATH, 48)
        subtitle_font = pygame.font.Font(FONT_PATH, 18)
        button_font = pygame.font.Font(FONT_PATH, 22)
        input_font = pygame.font.Font(FONT_PATH, 20)
    else:
        title_font = pygame.font.SysFont("Arial", 48)
        subtitle_font = pygame.font.SysFont("Arial", 18)
        button_font = pygame.font.SysFont("Arial", 22)
        input_font = pygame.font.SysFont("Arial", 20)

    # Load translations and settings
    trans = load_translations()
    from settings import load_settings, settings_screen
    settings = load_settings()
    lang = settings["language"]

    # Apply fullscreen setting
    if settings["fullscreen"]:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        screen_width, screen_height = screen.get_size()

    # Load random background
    bg_images = []
    if os.path.isdir(HOME_BG_DIR):
        for f in os.listdir(HOME_BG_DIR):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                try:
                    bg_images.append(pygame.image.load(os.path.join(HOME_BG_DIR, f)))
                except Exception:
                    pass

    bg_img = None
    bg_scaled = None
    if bg_images:
        bg_img = random.choice(bg_images)
        bg_scaled = pygame.transform.scale(bg_img, (screen_width, screen_height))

    # Init default account
    init_default_account()

    # UI layout
    center_x = screen_width // 2
    column_x = center_x - BUTTON_WIDTH // 2
    title_y = screen_height // 6
    input_start_y = title_y + 100

    username_input = TextInput(column_x, input_start_y, INPUT_WIDTH, INPUT_HEIGHT,
                               input_font, is_password=False)
    password_input = TextInput(column_x, input_start_y + 70, INPUT_WIDTH, INPUT_HEIGHT,
                               input_font, is_password=True)

    login_btn = Button(column_x, input_start_y + 140, BUTTON_WIDTH, BUTTON_HEIGHT,
                       "", button_font)
    register_btn = Button(column_x, input_start_y + 200, BUTTON_WIDTH, BUTTON_HEIGHT,
                          "", button_font)
    settings_btn = Button(column_x, input_start_y + 270, BUTTON_WIDTH, BUTTON_HEIGHT,
                          "", button_font)

    inputs = [username_input, password_input]
    focused = 0

    # Modal state (for default-steve login confirmation)
    show_modal = False
    modal_confirm_btn = Button(0, 0, 120, 40, "", button_font)
    modal_cancel_btn = Button(0, 0, 120, 40, "", button_font)

    message = ""
    message_color = SUCCESS_COLOR

    pygame.mouse.set_visible(True)

    running = True
    while running:
        clock.tick(60)

        username_input.update()
        password_input.update()

        # Update labels
        username_label = t(trans, "homepage_username", lang)
        password_label = t(trans, "homepage_password", lang)
        login_btn.set_text(t(trans, "homepage_login", lang))
        register_btn.set_text(t(trans, "homepage_register", lang))
        settings_btn.set_text(t(trans, "homepage_settings", lang))
        title_text = t(trans, "homepage_title", lang)
        subtitle_text = t(trans, "homepage_copyright", lang)

        # Update modal button labels/text
        modal_text = t(trans, "homepage_default_login", lang)
        modal_confirm_btn.set_text(t(trans, "homepage_confirm", lang))
        modal_cancel_btn.set_text(t(trans, "homepage_cancel", lang))

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            elif event.type == pygame.KEYDOWN:
                # Ctrl+L toggles language (only when modal not open)
                if event.key == pygame.K_l and (event.mod & pygame.KMOD_CTRL) and not show_modal:
                    lang = "en" if lang == "zh" else "zh"
                    message = ""
                elif show_modal:
                    # Modal open: Esc = cancel, Enter = confirm
                    if event.key == pygame.K_ESCAPE:
                        show_modal = False
                    elif event.key == pygame.K_RETURN:
                        show_modal = False
                        return (DEFAULT_USER, lang, settings, screen_width, screen_height)
                elif event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_TAB:
                    focused = (focused + 1) % len(inputs)
                    for i, inp in enumerate(inputs):
                        inp.active = (i == focused)
                elif event.key == pygame.K_RETURN:
                    username = username_input.text.strip()
                    password = password_input.text.strip()
                    if not username and not password:
                        show_modal = True
                    elif not username:
                        message = t(trans, "homepage_input_username", lang)
                        message_color = ERROR_COLOR
                    elif not password:
                        message = t(trans, "homepage_input_password", lang)
                        message_color = ERROR_COLOR
                    elif login(username, password):
                        message = t(trans, "homepage_login_success", lang)
                        message_color = SUCCESS_COLOR
                        pygame.time.delay(500)
                        return (username, lang, settings, screen_width, screen_height)
                    else:
                        message = t(trans, "homepage_login_failed", lang)
                        message_color = ERROR_COLOR
                else:
                    for inp in inputs:
                        if inp.active:
                            inp.handle_event(event)

            elif event.type == pygame.VIDEORESIZE and not settings["fullscreen"]:
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode(
                    (screen_width, screen_height), pygame.RESIZABLE)
                if bg_img:
                    bg_scaled = pygame.transform.scale(bg_img,
                                                       (screen_width, screen_height))
                center_x = screen_width // 2
                column_x = center_x - BUTTON_WIDTH // 2
                username_input.rect.x = column_x
                password_input.rect.x = column_x
                login_btn.rect.x = column_x
                register_btn.rect.x = column_x
                settings_btn.rect.x = column_x

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if show_modal:
                    # Modal buttons
                    if modal_confirm_btn.handle_event(event):
                        show_modal = False
                        return (DEFAULT_USER, lang, settings,
                                screen_width, screen_height)
                    elif modal_cancel_btn.handle_event(event):
                        show_modal = False
                else:
                    for i, inp in enumerate(inputs):
                        inp.handle_event(event)
                    if login_btn.handle_event(event):
                        username = username_input.text.strip()
                        password = password_input.text.strip()
                        if not username and not password:
                            show_modal = True
                        elif not username:
                            message = t(trans, "homepage_input_username", lang)
                            message_color = ERROR_COLOR
                        elif not password:
                            message = t(trans, "homepage_input_password", lang)
                            message_color = ERROR_COLOR
                        elif login(username, password):
                            message = t(trans, "homepage_login_success", lang)
                            message_color = SUCCESS_COLOR
                            pygame.time.delay(500)
                            return (username, lang, settings,
                                    screen_width, screen_height)
                        else:
                            message = t(trans, "homepage_login_failed", lang)
                            message_color = ERROR_COLOR
                    elif register_btn.handle_event(event):
                        username = username_input.text.strip()
                        password = password_input.text.strip()
                        if not username:
                            message = t(trans, "homepage_input_username", lang)
                            message_color = ERROR_COLOR
                        elif not password:
                            message = t(trans, "homepage_input_password", lang)
                            message_color = ERROR_COLOR
                        elif len(password) < 4:
                            message = t(trans, "homepage_password_short", lang)
                            message_color = ERROR_COLOR
                        elif register(username, password):
                            message = t(trans, "homepage_register_success", lang)
                            message_color = SUCCESS_COLOR
                        else:
                            message = t(trans, "homepage_register_exists", lang)
                            message_color = ERROR_COLOR
                    elif settings_btn.handle_event(event):
                        result = settings_screen(screen, screen_width, screen_height,
                                                 settings)
                        if result is None:
                            return None
                        settings, screen, screen_width, screen_height = result
                        lang = settings["language"]
                        if bg_img:
                            bg_scaled = pygame.transform.scale(
                                bg_img, (screen_width, screen_height))
                        center_x = screen_width // 2
                        column_x = center_x - BUTTON_WIDTH // 2
                        for obj in (username_input, password_input,
                                    login_btn, register_btn, settings_btn):
                            obj.rect.x = column_x
                        message = ""

            elif event.type == pygame.MOUSEMOTION:
                if show_modal:
                    modal_confirm_btn.handle_event(event)
                    modal_cancel_btn.handle_event(event)
                else:
                    login_btn.handle_event(event)
                    register_btn.handle_event(event)
                    settings_btn.handle_event(event)

        # --- RENDER ---
        if bg_scaled:
            screen.blit(bg_scaled, (0, 0))
        else:
            screen.fill((20, 20, 30))

        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill(BG_COLOR)
        screen.blit(overlay, (0, 0))

        # Title
        title_surf = title_font.render(title_text, True, ACCENT_COLOR)
        title_rect = title_surf.get_rect(center=(center_x, title_y))
        shadow = title_font.render(title_text, True, (0, 0, 0))
        screen.blit(shadow, (title_rect.x + 2, title_rect.y + 2))
        screen.blit(title_surf, title_rect)

        # Labels
        username_lbl = input_font.render(username_label + ":", True, TEXT_COLOR)
        screen.blit(username_lbl, (column_x, input_start_y - 22))
        password_lbl = input_font.render(password_label + ":", True, TEXT_COLOR)
        screen.blit(password_lbl, (column_x, input_start_y + 48))

        # Inputs
        username_input.draw(screen)
        password_input.draw(screen)

        # Buttons
        login_btn.draw(screen)
        register_btn.draw(screen)
        settings_btn.draw(screen)

        # Message
        if message:
            msg_surf = input_font.render(message, True, message_color)
            msg_rect = msg_surf.get_rect(center=(center_x, input_start_y + 320))
            screen.blit(msg_surf, msg_rect)

        # Copyright
        copy_surf = subtitle_font.render(subtitle_text, True, (150, 150, 150))
        copy_rect = copy_surf.get_rect(center=(center_x, screen_height - 30))
        screen.blit(copy_surf, copy_rect)

        # --- Modal dialog ---
        if show_modal:
            # Dim background
            dim = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 140))
            screen.blit(dim, (0, 0))

            # Modal box
            modal_w = 400
            modal_h = 160
            modal_x = center_x - modal_w // 2
            modal_y = screen_height // 2 - modal_h // 2
            modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
            pygame.draw.rect(screen, (45, 45, 45), modal_rect, border_radius=10)
            pygame.draw.rect(screen, ACCENT_COLOR, modal_rect, 2, border_radius=10)

            # Modal text
            modal_surf = input_font.render(modal_text, True, TEXT_COLOR)
            modal_text_rect = modal_surf.get_rect(center=(center_x, modal_y + 40))
            screen.blit(modal_surf, modal_text_rect)

            # Buttons
            btn_gap = 20
            total_w = 120 * 2 + btn_gap
            btn_start_x = center_x - total_w // 2
            btn_y = modal_y + modal_h - 60

            modal_confirm_btn.rect.topleft = (btn_start_x, btn_y)
            modal_cancel_btn.rect.topleft = (btn_start_x + 120 + btn_gap, btn_y)

            modal_confirm_btn.draw(screen)
            modal_cancel_btn.draw(screen)

        pygame.display.flip()

    return None