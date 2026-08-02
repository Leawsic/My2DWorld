"""
My2DWorld - A 2D Minecraft-style infinite terrain explorer.
Uses pygame for rendering and hand-crafted noise for terrain generation.
"""

import json
import math
import os
import sys
import pygame

from world import World, GRASS, DIRT, STONE, COBBLESTONE, MOSSY_COBBLESTONE, BEDROCK
from player import BODY_HALF_HEIGHT, Player
from homepage import homepage
from logger import init_log, log_event, log_game_start, log_game_end, log_pause, log_resume
from gamemodes import SPECTATOR, CREATIVE, MODE_LIST, create_mode
from runtime import PROJECT_ROOT, WORLDS_DIR, ensure_runtime_data
from chat import Chat, execute_command

# Constants
INITIAL_WIDTH = 1024
INITIAL_HEIGHT = 768
DEFAULT_BLOCK_SIZE = 32
MIN_BLOCK_SIZE = 32
FPS = 60
VIEW_DISTANCE_CHUNKS = 8

ZOOM_FACTOR = 1.15
HIGHLIGHT_COLOR = (255, 255, 255)
HIGHLIGHT_WIDTH = 2

# Project resource paths
FONT_PATH = os.path.join(PROJECT_ROOT, "fonts", "LXGWWenKai-Regular.ttf")
BLOCK_CONFIG_PATH = os.path.join(PROJECT_ROOT, "translate", "block.json")
TRANSLATE_CONFIG_PATH = os.path.join(PROJECT_ROOT, "translate", "translate.json")
GUI_DIR = os.path.join(PROJECT_ROOT, "image", "gui")


def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log_event(f"Warning: config file '{path}' not found")
        return {}
    except json.JSONDecodeError as e:
        log_event(f"Warning: failed to parse '{path}': {e}")
        return {}


def load_textures(tex_dir: str | None = None) -> dict:
    if tex_dir is None:
        tex_dir = os.path.join(PROJECT_ROOT, "image", "block")
    textures = {}
    if not os.path.isdir(tex_dir):
        log_event(f"Warning: texture directory '{tex_dir}' not found")
        return textures
    for fname in os.listdir(tex_dir):
        if fname.endswith(".png"):
            path = os.path.join(tex_dir, fname)
            try:
                img = pygame.image.load(path).convert_alpha()
                key = fname.rsplit(".", 1)[0]
                textures[key] = img
                log_event(f"  Loaded texture: {key} ({img.get_width()}x{img.get_height()})")
            except Exception as e:
                log_event(f"  Failed to load {path}: {e}")
    return textures


def get_texture_or_fallback(textures: dict, block_type: str,
                            block_size: int, color_map: dict) -> pygame.Surface:
    if block_type in textures:
        raw = textures[block_type]
        return pygame.transform.scale(raw, (block_size, block_size))
    info = color_map.get(block_type, {})
    color = info.get("color", [200, 0, 200]) if isinstance(info, dict) else (200, 0, 200)
    surf = pygame.Surface((block_size, block_size))
    surf.fill(color)
    pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), 1)
    return surf


def world_save_path(username: str, world_name: str) -> str:
    """Get the save file path for a world (under run/worlds/)."""
    safe_user = "".join(c for c in username if c.isalnum() or c in ("-", "_"))
    safe_world = "".join(c for c in world_name if c.isalnum() or c in ("-", "_"))
    return os.path.join(WORLDS_DIR, f"{safe_user or 'player'}_{safe_world or 'world'}.json")


def load_world_save(username: str, world_name: str):
    """
    Load a world save file.
    Returns dict with 'player_x', 'player_y', 'broken_blocks' or None if absent.
    """
    path = world_save_path(username, world_name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        log_event(f"Warning: failed to load save {path}: {e}")
        return None


def save_world_state(username: str, world_name: str, player, world):
    """
    Save player foot position and broken block coordinates to disk.
    """
    ensure_runtime_data()
    os.makedirs(WORLDS_DIR, exist_ok=True)
    px, py = player.get_pos()
    data = {
        "player_x": px,
        "player_y": py,
        "position_anchor": "feet_v2",
        "broken_blocks": [[bx, by] for bx, by in sorted(world.broken_blocks)],
    }
    path = world_save_path(username, world_name)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_event(f"World Saved: user={username} world={world_name} "
                  f"pos=({px:.1f},{py:.1f}) blocks={len(world.broken_blocks)}")
    except Exception as e:
        log_event(f"Warning: failed to save world {path}: {e}")


def load_gui_textures() -> dict:
    gui = {}
    if not os.path.isdir(GUI_DIR):
        return gui
    for fname in os.listdir(GUI_DIR):
        if fname.endswith(".png"):
            path = os.path.join(GUI_DIR, fname)
            try:
                img = pygame.image.load(path).convert_alpha()
                key = fname.rsplit(".", 1)[0]
                gui[key] = img
                log_event(f"  Loaded GUI: {key} ({img.get_width()}x{img.get_height()})")
            except Exception as e:
                log_event(f"  Failed to load {path}: {e}")
    return gui


def start_game(screen, screen_width, screen_height, username, lang, settings, world_name, mode_name=SPECTATOR):
    """
    Main game loop after successful login.
    Returns "homepage" to return to the main menu, or False to quit the app.
    """
    log_game_start(username, world_name)
    log_event(f"Game Mode: user={username} mode={mode_name}")

    # Load configs
    block_config = load_json(BLOCK_CONFIG_PATH)
    translate_config = load_json(TRANSLATE_CONFIG_PATH)

    # Helper: translate a gui key
    def t(key, **kwargs):
        texts = translate_config.get("gui", {}).get(key, {})
        text = texts.get(lang, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        return text

    # Helper: translate a block name
    def block_name(block_type):
        entries = translate_config.get("blocks", {}).get(block_type, {})
        return entries.get(lang, block_type)

    # Build color map
    color_map = {}
    for key, info in block_config.items():
        if isinstance(info, dict) and "color" in info:
            color_map[key] = info

    gui_section = translate_config.get("gui", {})
    window_title_texts = gui_section.get("window_title", {})
    mode_texts = gui_section.get("mode_spectator", {})
    controls_texts = gui_section.get("controls_hint", {})
    welcome_texts = gui_section.get("welcome", {})
    current_lang = lang

    is_fullscreen = settings["fullscreen"]
    key_bindings = settings.get("key_bindings", {})

    def configured_key(action, fallback):
        name = key_bindings.get(action, fallback)
        aliases = {"space": pygame.K_SPACE, "left": pygame.K_LEFT,
                   "right": pygame.K_RIGHT, "up": pygame.K_UP,
                   "down": pygame.K_DOWN}
        if name in aliases:
            return aliases[name]
        key_name = str(name)
        key = getattr(pygame, f"K_{key_name.lower()}", None)
        if key is None:
            key = getattr(pygame, f"K_{key_name.upper()}", None)
        if key is not None:
            return key
        fallback_name = str(fallback)
        key = getattr(pygame, f"K_{fallback_name.lower()}", None)
        if key is None:
            key = getattr(pygame, f"K_{fallback_name.upper()}", None)
        return key

    debug_key = configured_key("debug", "f3")
    mode_key = configured_key("mode", "f4")
    chat_key = configured_key("chat", "t")

    pygame.display.set_caption(window_title_texts.get(current_lang, "My2DWorld"))
    clock = pygame.time.Clock()

    # Load font
    if os.path.isfile(FONT_PATH):
        debug_font = pygame.font.Font(FONT_PATH, 14)
        name_font = pygame.font.Font(FONT_PATH, 20)
        mode_font = pygame.font.Font(FONT_PATH, 18)
        welcome_font = pygame.font.Font(FONT_PATH, 16)
        pause_title_font = pygame.font.Font(FONT_PATH, 36)
        pause_button_font = pygame.font.Font(FONT_PATH, 22)
    else:
        debug_font = pygame.font.SysFont("Arial", 14)
        name_font = pygame.font.SysFont("Arial", 20)
        mode_font = pygame.font.SysFont("Arial", 18)
        welcome_font = pygame.font.SysFont("Arial", 16)
        pause_title_font = pygame.font.SysFont("Arial", 36)
        pause_button_font = pygame.font.SysFont("Arial", 22)

    # Load textures
    textures = load_textures()

    # Load GUI textures
    gui_textures = load_gui_textures()

    # Create world and player
    world = World(view_distance_chunks=VIEW_DISTANCE_CHUNKS)

    # Load saved world state (player position + broken blocks)
    save_data = load_world_save(username, world_name)
    if save_data:
        try:
            start_px = float(save_data.get("player_x", 0))
            start_py = float(save_data.get("player_y", 0))
            anchor = save_data.get("position_anchor")
            # Older saves used a center anchor. The first foot-anchor revision
            # still used the wrong block-bottom convention and was one block high.
            if anchor == "feet":
                start_py -= 1
            elif anchor != "feet_v2":
                start_py -= BODY_HALF_HEIGHT + 1
        except (TypeError, ValueError):
            start_px, start_py = 0, 0
        broken = save_data.get("broken_blocks", [])
        world.apply_broken_blocks(broken if isinstance(broken, list) else [])
        log_event(f"World Loaded: user={username} world={world_name} "
                  f"pos=({start_px:.1f},{start_py:.1f}) blocks={len(world.broken_blocks)}")
    else:
        start_px, start_py = 0, world.get_surface_height(0) + 0.001

    player = Player(start_x=start_px, start_y=start_py, settings=settings)
    spawn_x, spawn_y = 0.0, world.get_surface_height(0) + 0.001
    void_settings = settings.get("void", {})
    void_death_y = float(void_settings.get("death_y", -10.0))
    void_damage = float(void_settings.get("damage", 20.0))
    world.update_view(player.x)

    # Zoom state
    block_size = DEFAULT_BLOCK_SIZE

    # Camera pan
    camera_offset_x = 0.0
    camera_offset_y = 0.0
    is_rmb_dragging = False
    rmb_drag_start_mouse = (0, 0)
    rmb_drag_start_offset = (0.0, 0.0)

    # Create the game mode instance
    current_mode = create_mode(mode_name, player, world, textures, username)

    running = True
    result = False  # Return value: False = quit app, "homepage" = back to menu
    paused = False
    show_debug = settings["debug_default"]
    f3_held = False
    f4_held = False
    combo_consumed = False
    chat = Chat(debug_font)
    pygame.mouse.set_visible(False)

    # Welcome message timer
    welcome_msg = welcome_texts.get(current_lang, "").format(name=username)
    welcome_timer = 180  # ~3 seconds

    while running:
        dt = clock.tick(FPS) / 16.667
        chat.update(dt / 60.0)
        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()
        mx, my = pygame.mouse.get_pos()

        pause_button_width = 220
        pause_button_height = 48
        resume_rect = pygame.Rect(
            screen_width // 2 - pause_button_width // 2,
            screen_height // 2 - 4,
            pause_button_width,
            pause_button_height,
        )
        home_rect = pygame.Rect(
            resume_rect.x,
            resume_rect.bottom + 14,
            pause_button_width,
            pause_button_height,
        )
        quit_rect = pygame.Rect(
            home_rect.x,
            home_rect.bottom + 14,
            pause_button_width,
            pause_button_height,
        )

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result = False
                running = False

            elif paused:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    paused = False
                    pygame.mouse.set_visible(False)
                    log_resume(username)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if resume_rect.collidepoint(event.pos):
                        paused = False
                        pygame.mouse.set_visible(False)
                        log_resume(username)
                    elif home_rect.collidepoint(event.pos):
                        result = "homepage"
                        running = False
                    elif quit_rect.collidepoint(event.pos):
                        result = False
                        running = False

            elif event.type == pygame.VIDEORESIZE and not is_fullscreen:
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode(
                    (screen_width, screen_height),
                    pygame.RESIZABLE
                )

            elif event.type == pygame.KEYDOWN:
                if chat.open:
                    command = chat.handle_event(event)
                    if command is not None:
                        if command.strip():
                            chat.add_message(f"> {command.strip()}" )
                        message, requested_mode, show_debug = execute_command(
                            command, player, current_mode.name, show_debug,
                            lambda value: setattr(player, "walk_speed", value),
                            lambda: player.reset(spawn_x, spawn_y),
                        )
                        chat.add_message(message)
                        if requested_mode != current_mode.name:
                            current_mode = create_mode(
                                requested_mode, player, world, textures, username
                            )
                    continue
                if event.key == pygame.K_ESCAPE:
                    paused = True
                    pygame.mouse.set_visible(True)
                    is_rmb_dragging = False
                    log_pause(username)
                elif event.key == debug_key:
                    if f3_held:
                        continue
                    f3_held = True
                    if f4_held:
                        combo_consumed = True
                        new_mode_name = CREATIVE if current_mode.name == SPECTATOR else SPECTATOR
                        log_event(f"Mode Switch: user={username} from={current_mode.name} to={new_mode_name}")
                        current_mode = create_mode(new_mode_name, player, world, textures, username)
                        camera_offset_x = 0.0
                        camera_offset_y = 0.0
                        is_rmb_dragging = False
                elif event.key == mode_key:
                    if f4_held:
                        continue
                    f4_held = True
                    if f3_held:
                        combo_consumed = True
                        new_mode_name = CREATIVE if current_mode.name == SPECTATOR else SPECTATOR
                        log_event(f"Mode Switch: user={username} from={current_mode.name} to={new_mode_name}")
                        current_mode = create_mode(new_mode_name, player, world, textures, username)
                        camera_offset_x = 0.0
                        camera_offset_y = 0.0
                        is_rmb_dragging = False
                elif event.key == chat_key:
                    chat.open_chat()
                elif event.key == pygame.K_SLASH:
                    chat.open_chat("/")
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        screen_width, screen_height = screen.get_size()
                    else:
                        screen_width = INITIAL_WIDTH
                        screen_height = INITIAL_HEIGHT
                        screen = pygame.display.set_mode(
                            (screen_width, screen_height), pygame.RESIZABLE
                        )
                elif event.key == pygame.K_l and (event.mod & pygame.KMOD_CTRL):
                    current_lang = "en" if current_lang == "zh" else "zh"
                    pygame.display.set_caption(
                        window_title_texts.get(current_lang, "My2DWorld")
                    )
                    welcome_msg = welcome_texts.get(current_lang, "").format(name=username)
                    # Update t/block_name closures
                    def t_updated(key, **kw):
                        texts = translate_config.get("gui", {}).get(key, {})
                        txt = texts.get(current_lang, key)
                        if kw:
                            try:
                                txt = txt.format(**kw)
                            except KeyError:
                                pass
                        return txt
                    t = t_updated

            elif event.type == pygame.KEYUP and event.key == debug_key:
                f3_held = False
                if not combo_consumed:
                    show_debug = not show_debug
                if not f4_held:
                    combo_consumed = False

            elif event.type == pygame.KEYUP and event.key == mode_key:
                f4_held = False
                if not f3_held:
                    combo_consumed = False

            elif event.type == pygame.MOUSEWHEEL:
                if chat.scroll(event.y):
                    continue
                if event.y > 0:
                    new_size = block_size * ZOOM_FACTOR
                    max_bs = max(min(screen_width, screen_height) / 2, DEFAULT_BLOCK_SIZE)
                    if new_size <= max_bs:
                        block_size = int(new_size)
                elif event.y < 0:
                    new_size = block_size / ZOOM_FACTOR
                    if new_size >= MIN_BLOCK_SIZE:
                        block_size = max(int(new_size), MIN_BLOCK_SIZE)

        # Right mouse drag: only in spectator mode
        if not paused and current_mode.name == SPECTATOR:
            if mouse_buttons[2]:
                if not is_rmb_dragging:
                    is_rmb_dragging = True
                    rmb_drag_start_mouse = (mx, my)
                    rmb_drag_start_offset = (camera_offset_x, camera_offset_y)
                else:
                    sx0, sy0 = rmb_drag_start_mouse
                    dx_px = mx - sx0
                    dy_px = my - sy0
                    camera_offset_x = rmb_drag_start_offset[0] - dx_px / block_size
                    camera_offset_y = rmb_drag_start_offset[1] + dy_px / block_size
            else:
                if is_rmb_dragging:
                    is_rmb_dragging = False
        elif not paused:
            # Reset drag state when not in spectator mode
            is_rmb_dragging = False

        px, py = player.get_pos()
        adjusted_cam_x = px + camera_offset_x
        if not paused:
            world.update_view(adjusted_cam_x)
        camera_x = adjusted_cam_x
        camera_y = py + camera_offset_y

        # Hovered block
        hovered_block = None
        hovered_wx = 0
        hovered_wy = 0
        hovered_sx = 0
        hovered_sy = 0
        hovered_info = None  # (wx, wy, block_type) for mode interaction
        cx_off = screen_width // 2
        cy_off = screen_height // 2
        world_mx = camera_x + (mx - cx_off) / block_size
        world_my = camera_y - (my - cy_off) / block_size
        wx = int(math.floor(world_mx))
        wy = int(math.ceil(world_my))
        if not paused and world_my > 0:
            bt = world.get_block(wx, wy)
            if bt:
                hovered_block = bt
                hovered_wx = wx
                hovered_wy = wy
                hovered_sx = int((wx - camera_x) * block_size + cx_off)
                hovered_sy = int((camera_y - wy) * block_size + cy_off)
                hovered_info = (wx, wy, bt)

        # Update current game mode (player physics, particles, block breaking)
        if not paused and not chat.open:
            current_mode.update(dt, keys, mouse_buttons, mx, my, block_size, hovered_info)
            if player.y < void_death_y:
                player.health -= void_damage * (dt / 60.0)
                if player.health <= 0:
                    player.reset(spawn_x, spawn_y)
                    chat.add_message("You died and respawned.")
        px, py = player.get_pos()
        camera_x = px + camera_offset_x
        camera_y = py + camera_offset_y

        # RENDER
        screen.fill((135, 206, 235))

        def draw_block(sx, sy, block_type):
            tex = get_texture_or_fallback(textures, block_type, block_size, color_map)
            screen.blit(tex, (sx, sy))

        world.render_blocks(camera_x, camera_y, screen_width, screen_height,
                            block_size, draw_block)

        if hovered_block:
            pygame.draw.rect(screen, HIGHLIGHT_COLOR,
                             (hovered_sx, hovered_sy, block_size, block_size),
                             HIGHLIGHT_WIDTH)

        if hovered_block:
            name = block_name(hovered_block)
            name_surf = name_font.render(name, True, (255, 255, 255))
            shadow_surf = name_font.render(name, True, (0, 0, 0))
            nx = (screen_width - name_surf.get_width()) // 2
            ny = 10
            screen.blit(shadow_surf, (nx + 1, ny + 1))
            screen.blit(name_surf, (nx, ny))

        # Render particles over blocks
        current_mode.render_particles(screen, camera_x, camera_y, block_size)

        # Render player entity (creative only)
        current_mode.render_player(screen, camera_x, camera_y, block_size)

        # Custom cursor
        if not paused:
            cursor_key = "mouse_right_spectator" if is_rmb_dragging else "mouse"
            cursor_img = gui_textures.get(cursor_key)
            if cursor_img:
                screen.blit(cursor_img, (mx, my))

        # Mode label (dynamic based on current mode)
        if current_mode.name == CREATIVE:
            mode_label_text = gui_section.get("mode_creative", {}).get(current_lang, "Creative")
        else:
            mode_label_text = mode_texts.get(current_lang, "Spectator")
        mode_surf = mode_font.render(mode_label_text, True, (255, 255, 255))
        mode_shadow = mode_font.render(mode_label_text, True, (0, 0, 0))
        mode_x = screen_width - mode_surf.get_width() - 10
        mode_y = screen_height - mode_surf.get_height() - 10
        screen.blit(mode_shadow, (mode_x + 1, mode_y + 1))
        screen.blit(mode_surf, (mode_x, mode_y))

        # Welcome message (fades out)
        if welcome_timer > 0 and not paused:
            welcome_timer -= 1
            alpha = min(255, welcome_timer * 2)
            welcome_surf = welcome_font.render(welcome_msg, True, (255, 255, 200))
            welcome_rect = welcome_surf.get_rect(center=(screen_width // 2, screen_height // 2 - 50))
            dark_overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, 80))
            screen.blit(dark_overlay, (0, 0))
            screen.blit(welcome_surf, welcome_rect)

        # Debug info
        if show_debug:
            zoom_pct = int(block_size / DEFAULT_BLOCK_SIZE * 100)
            def tref(key, **kw):
                texts = translate_config.get("gui", {}).get(key, {})
                txt = texts.get(current_lang, key)
                if kw:
                    try:
                        txt = txt.format(**kw)
                    except KeyError:
                        pass
                return txt
            hover_debug = ""
            if hovered_block:
                name = block_name(hovered_block)
                hover_debug = tref("debug_hover", name=name)
            # Controls hint depends on current mode
            if current_mode.name == CREATIVE:
                controls_line = gui_section.get("controls_hint", {}).get(
                    current_lang, "")
            else:
                controls_line = controls_texts.get(current_lang, "")
            lines = [
                tref("debug_fps", fps=clock.get_fps()),
                tref("debug_mode", mode=mode_label_text),
                tref("debug_world", name=world_name),
                tref("debug_player", x=px, y=py),
                tref("debug_camera", x=camera_x, y=camera_y),
                tref("debug_mouse", mx=mx, my=my, wx=wx, wy=wy) + hover_debug,
                tref("debug_zoom", pct=zoom_pct),
                tref("debug_window", w=screen_width, h=screen_height) +
                (tref("debug_fullscreen") if is_fullscreen else ""),
                tref("debug_chunks", n=len(world.chunks)),
                tref("debug_textures", n=len(textures)),
                tref("debug_lang"),
                controls_line,
            ]
            for i, line in enumerate(lines):
                text_surf = debug_font.render(line, True, (255, 255, 255))
                shadow = debug_font.render(line, True, (0, 0, 0))
                screen.blit(shadow, (11, 11 + i * 18))
                screen.blit(text_surf, (10, 10 + i * 18))

        if paused:
            overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            def pause_text(key, fallback):
                return gui_section.get(key, {}).get(current_lang, fallback)

            title_surf = pause_title_font.render(
                pause_text("pause_title", "Paused"), True, (255, 255, 255)
            )
            screen.blit(title_surf, title_surf.get_rect(
                center=(screen_width // 2, screen_height // 2 - 62)
            ))

            for rect, label in (
                (resume_rect, pause_text("pause_resume", "Resume")),
                (home_rect, pause_text("pause_homepage", "Homepage")),
                (quit_rect, pause_text("pause_quit", "Quit")),
            ):
                hovered = rect.collidepoint((mx, my))
                color = (70, 70, 70) if hovered else (50, 50, 50)
                pygame.draw.rect(screen, color, rect, border_radius=6)
                pygame.draw.rect(screen, (100, 200, 255), rect, 2, border_radius=6)
                label_surf = pause_button_font.render(label, True, (255, 255, 255))
                screen.blit(label_surf, label_surf.get_rect(center=rect.center))

        chat.draw(screen, screen_width, screen_height)

        pygame.display.flip()

    # Save world state (player position + broken blocks) before exiting
    save_world_state(username, world_name, player, world)

    # Log game end before returning
    if result == "homepage":
        log_game_end(username, "homepage")
    else:
        log_game_end(username, "quit")

    return result


def main():
    """Main entry point: show homepage, then start game.
    Loops back to the homepage when the user selects "back to menu" from pause."""
    pygame.init()

    # Initialize logging with a system-time-based filename (run/logs/YYYY-MM-DD_HH-MM-SS.log)
    init_log()

    screen_width = INITIAL_WIDTH
    screen_height = INITIAL_HEIGHT

    screen = pygame.display.set_mode(
        (screen_width, screen_height),
        pygame.RESIZABLE
    )
    pygame.display.set_caption("My2DWorld")

    while True:
        # Show homepage → returns (username, lang, settings, screen_width, screen_height) or None
        result = homepage(screen, screen_width, screen_height)

        if result is None:
            # User quit from homepage
            pygame.quit()
            sys.exit()

        username, lang, settings, actual_width, actual_height = result

        from world_menu import world_menu
        world_result = world_menu(screen, actual_width, actual_height, username, lang)
        if world_result is None:
            break
        if world_result == "back":
            screen_width, screen_height = actual_width, actual_height
            continue
        world_name, mode_name, screen, actual_width, actual_height = world_result

        # Start the game with actual screen dimensions (fixes maximize/fullscreen scaling)
        game_result = start_game(screen, actual_width, actual_height,
                                 username, lang, settings, world_name, mode_name)

        if game_result != "homepage":
            # User quit the app from the pause menu
            break

        # The game may have resized or maximized the display. Read the live
        # surface dimensions instead of reusing its pre-game cached size.
        screen_width, screen_height = screen.get_size()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
