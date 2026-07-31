"""Post-login world creation, selection, editing, and deletion screen."""

import json
import os
from datetime import datetime

import pygame

from homepage import (
    ACCENT_COLOR,
    BG_COLOR,
    BUTTON_HEIGHT,
    BUTTON_WIDTH,
    ERROR_COLOR,
    FONT_PATH,
    TEXT_COLOR,
    Button,
    TextInput,
    load_translations,
    t,
)
from logger import log_event
from runtime import WORLDS_DIR, ensure_runtime_data

MAX_WORLD_NAME_LENGTH = 24


def _worlds_path(username):
    safe_username = "".join(
        char for char in username if char.isalnum() or char in ("-", "_")
    )
    return os.path.join(WORLDS_DIR, f"{safe_username or 'player'}.json")


def load_worlds(username):
    ensure_runtime_data()
    try:
        with open(_worlds_path(username), "r", encoding="utf-8") as file:
            data = json.load(file)
        worlds = data.get("worlds", [])
        return [world for world in worlds if isinstance(world, dict)
                and isinstance(world.get("name"), str)]
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as error:
        log_event(f"Warning: failed to load worlds for user={username}: {error}")
        return []


def save_worlds(username, worlds):
    try:
        ensure_runtime_data()
        os.makedirs(WORLDS_DIR, exist_ok=True)
        with open(_worlds_path(username), "w", encoding="utf-8") as file:
            json.dump({"worlds": worlds}, file, ensure_ascii=False, indent=2)
        return True
    except OSError as error:
        log_event(f"Warning: failed to save worlds for user={username}: {error}")
        return False


def world_menu(screen, screen_width, screen_height, username, lang):
    """Return a selected world tuple, ``"back"``, or ``None`` on quit."""
    clock = pygame.time.Clock()
    if os.path.isfile(FONT_PATH):
        title_font = pygame.font.Font(FONT_PATH, 42)
        button_font = pygame.font.Font(FONT_PATH, 18)
        input_font = pygame.font.Font(FONT_PATH, 20)
    else:
        title_font = pygame.font.SysFont("Arial", 42)
        button_font = pygame.font.SysFont("Arial", 18)
        input_font = pygame.font.SysFont("Arial", 20)

    trans = load_translations()
    worlds = load_worlds(username)
    scroll_index = 0
    editing_index = None
    creating_world = False
    message = ""
    world_name_input = TextInput(0, 0, BUTTON_WIDTH, 40, input_font,
                                 max_length=MAX_WORLD_NAME_LENGTH)
    pygame.mouse.set_visible(True)

    while True:
        clock.tick(60)
        center_x = screen_width // 2
        title_y = screen_height // 6
        content_y = title_y + 75
        row_height = 56
        list_top = content_y + 60
        list_bottom = screen_height - 88
        list_height = max(56, list_bottom - list_top)
        visible_count = max(1, list_height // row_height)
        max_scroll = max(0, len(worlds) - visible_count)
        scroll_index = min(scroll_index, max_scroll)

        create_btn = Button(center_x - BUTTON_WIDTH // 2, content_y,
                            BUTTON_WIDTH, BUTTON_HEIGHT, "", button_font)
        back_btn = Button(center_x - BUTTON_WIDTH // 2, screen_height - 65,
                          BUTTON_WIDTH, 40, "", button_font)
        create_btn.set_text(t(trans, "world_create", lang))
        back_btn.set_text(t(trans, "world_back", lang))

        row_controls = []
        for visible_row, world_index in enumerate(
                range(scroll_index, min(len(worlds), scroll_index + visible_count))):
            y = list_top + visible_row * row_height
            enter_btn = Button(center_x - BUTTON_WIDTH // 2, y,
                               BUTTON_WIDTH - 126, 46,
                               worlds[world_index]["name"], button_font)
            edit_btn = Button(enter_btn.rect.right + 8, y, 54, 46,
                              t(trans, "world_edit", lang), button_font)
            delete_btn = Button(edit_btn.rect.right + 8, y, 54, 46,
                                t(trans, "world_delete", lang), button_font)
            row_controls.append((world_index, enter_btn, edit_btn, delete_btn))

        if editing_index is not None:
            world_name_input.rect.topleft = (center_x - BUTTON_WIDTH // 2,
                                             content_y + 60)
            confirm_btn = Button(center_x - BUTTON_WIDTH // 2, content_y + 110,
                                 BUTTON_WIDTH, BUTTON_HEIGHT, "", button_font)
            cancel_btn = Button(center_x - BUTTON_WIDTH // 2, content_y + 166,
                                BUTTON_WIDTH, 40, "", button_font)
            confirm_btn.set_text(t(trans, "world_edit_confirm", lang))
            cancel_btn.set_text(t(trans, "world_cancel", lang))
        else:
            confirm_btn = cancel_btn = None

        mouse_pos = pygame.mouse.get_pos()
        buttons = [create_btn, back_btn]
        for _, enter_btn, edit_btn, delete_btn in row_controls:
            buttons.extend((enter_btn, edit_btn, delete_btn))
        if confirm_btn:
            buttons.extend((confirm_btn, cancel_btn))
        for button in buttons:
            button.hover = button.rect.collidepoint(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode((screen_width, screen_height),
                                                 pygame.RESIZABLE)
                continue

            if event.type == pygame.MOUSEWHEEL and editing_index is None:
                scroll_index = max(0, min(max_scroll, scroll_index - event.y))
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if editing_index is not None:
                        if creating_world:
                            worlds.pop(editing_index)
                        editing_index = None
                        creating_world = False
                        world_name_input.active = False
                        message = ""
                    else:
                        return "back"
                elif editing_index is not None and event.key == pygame.K_RETURN:
                    world_name_input.handle_event(event)
                    world_name_input.text = world_name_input.text[:MAX_WORLD_NAME_LENGTH]
                    new_name = world_name_input.text.strip()
                    if not new_name:
                        message = t(trans, "world_name_required", lang)
                    elif any(i != editing_index and world["name"] == new_name
                             for i, world in enumerate(worlds)):
                        message = t(trans, "world_name_exists", lang)
                    else:
                        worlds[editing_index]["name"] = new_name
                        if save_worlds(username, worlds):
                            event_name = "World Created" if creating_world else "World Renamed"
                            log_event(f"{event_name}: user={username} world={new_name}")
                            if creating_world:
                                return new_name, screen, screen_width, screen_height
                            editing_index = None
                            creating_world = False
                            world_name_input.active = False
                            message = ""
                        else:
                            message = t(trans, "world_save_failed", lang)
                elif editing_index is not None:
                    world_name_input.handle_event(event)
                    world_name_input.text = world_name_input.text[:MAX_WORLD_NAME_LENGTH]

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if editing_index is not None:
                    world_name_input.handle_event(event)
                    world_name_input.text = world_name_input.text[:MAX_WORLD_NAME_LENGTH]
                    if confirm_btn.handle_event(event):
                        new_name = world_name_input.text.strip()
                        if not new_name:
                            message = t(trans, "world_name_required", lang)
                        elif any(i != editing_index and world["name"] == new_name
                                 for i, world in enumerate(worlds)):
                            message = t(trans, "world_name_exists", lang)
                        else:
                            worlds[editing_index]["name"] = new_name
                            if save_worlds(username, worlds):
                                event_name = "World Created" if creating_world else "World Renamed"
                                log_event(f"{event_name}: user={username} world={new_name}")
                                if creating_world:
                                    return new_name, screen, screen_width, screen_height
                                editing_index = None
                                creating_world = False
                                world_name_input.active = False
                                message = ""
                            else:
                                message = t(trans, "world_save_failed", lang)
                    elif cancel_btn.handle_event(event):
                        if creating_world:
                            worlds.pop(editing_index)
                        editing_index = None
                        creating_world = False
                        world_name_input.active = False
                        message = ""
                elif create_btn.handle_event(event):
                    worlds.append({"name": "", "created_at": datetime.now().isoformat(timespec="seconds")})
                    editing_index = len(worlds) - 1
                    creating_world = True
                    world_name_input.text = ""
                    world_name_input.cursor_index = 0
                    world_name_input.active = True
                    message = ""
                elif back_btn.handle_event(event):
                    return "back"
                else:
                    for world_index, enter_btn, edit_btn, delete_btn in row_controls:
                        if enter_btn.handle_event(event):
                            name = worlds[world_index]["name"]
                            log_event(f"World Entered: user={username} world={name}")
                            return name, screen, screen_width, screen_height
                        if edit_btn.handle_event(event):
                            editing_index = world_index
                            creating_world = False
                            world_name_input.text = worlds[world_index]["name"]
                            world_name_input.cursor_index = len(world_name_input.text)
                            world_name_input.active = True
                            message = ""
                        elif delete_btn.handle_event(event):
                            name = worlds[world_index]["name"]
                            worlds.pop(world_index)
                            if save_worlds(username, worlds):
                                log_event(f"World Deleted: user={username} world={name}")
                                scroll_index = min(scroll_index, max(0, len(worlds) - visible_count))
                            else:
                                worlds.insert(world_index, {"name": name})
                                message = t(trans, "world_save_failed", lang)
                            break

            elif event.type == pygame.MOUSEMOTION:
                for button in buttons:
                    button.handle_event(event)

        screen.fill((20, 20, 30))
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill(BG_COLOR)
        screen.blit(overlay, (0, 0))
        title_surf = title_font.render(t(trans, "world_menu_title", lang), True, ACCENT_COLOR)
        screen.blit(title_surf, title_surf.get_rect(center=(center_x, title_y)))

        if confirm_btn is not None:
            label = input_font.render(t(trans, "world_name", lang), True, TEXT_COLOR)
            screen.blit(label, (world_name_input.rect.x, world_name_input.rect.y - 26))
            world_name_input.draw(screen)
            confirm_btn.draw(screen)
            cancel_btn.draw(screen)
        else:
            create_btn.draw(screen)
            for _, enter_btn, edit_btn, delete_btn in row_controls:
                enter_btn.draw(screen)
                edit_btn.draw(screen)
                delete_btn.draw(screen)
            if not worlds:
                empty = input_font.render(t(trans, "world_empty", lang), True, TEXT_COLOR)
                screen.blit(empty, empty.get_rect(center=(center_x, list_top + 35)))
            elif max_scroll:
                track = pygame.Rect(center_x + BUTTON_WIDTH // 2 + 10,
                                    list_top, 5, list_height)
                thumb_height = max(24, int(list_height * visible_count / len(worlds)))
                thumb_y = track.y + int(
                    (track.height - thumb_height) * scroll_index / max_scroll
                )
                pygame.draw.rect(screen, (90, 90, 90), track, border_radius=2)
                pygame.draw.rect(screen, ACCENT_COLOR,
                                 (track.x, thumb_y, track.width, thumb_height),
                                 border_radius=2)
            back_btn.draw(screen)

        if message:
            message_surf = input_font.render(message, True, ERROR_COLOR)
            screen.blit(message_surf, message_surf.get_rect(
                center=(center_x, min(screen_height - 25, list_bottom + 25))))

        pygame.display.flip()
