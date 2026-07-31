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
from player import Player
from homepage import homepage

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

# New file paths
FONT_PATH = "fonts/LXGWWenKai-Regular.ttf"
BLOCK_CONFIG_PATH = "translate/block.json"
TRANSLATE_CONFIG_PATH = "translate/translate.json"
GUI_DIR = "image/gui"


class GameMode:
    SPECTATOR = "spectator"


def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: config file '{path}' not found")
        return {}
    except json.JSONDecodeError as e:
        print(f"Warning: failed to parse '{path}': {e}")
        return {}


def load_textures(tex_dir: str = "image/block") -> dict:
    textures = {}
    if not os.path.isdir(tex_dir):
        print(f"Warning: texture directory '{tex_dir}' not found")
        return textures
    for fname in os.listdir(tex_dir):
        if fname.endswith(".png"):
            path = os.path.join(tex_dir, fname)
            try:
                img = pygame.image.load(path).convert_alpha()
                key = fname.rsplit(".", 1)[0]
                textures[key] = img
                print(f"  Loaded texture: {key} ({img.get_width()}x{img.get_height()})")
            except Exception as e:
                print(f"  Failed to load {path}: {e}")
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
                print(f"  Loaded GUI: {key} ({img.get_width()}x{img.get_height()})")
            except Exception as e:
                print(f"  Failed to load {path}: {e}")
    return gui


def start_game(screen, screen_width, screen_height, username, lang, settings):
    """
    Main game loop after successful login.
    """
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
    start_surface = world.get_surface_height(0)
    player = Player(start_x=0, start_y=start_surface + 3)
    world.update_view(player.x)

    # Zoom state
    block_size = DEFAULT_BLOCK_SIZE

    # Camera pan
    camera_offset_x = 0.0
    camera_offset_y = 0.0
    is_rmb_dragging = False
    rmb_drag_start_mouse = (0, 0)
    rmb_drag_start_offset = (0.0, 0.0)

    game_mode = GameMode.SPECTATOR
    mode_list = [GameMode.SPECTATOR]
    mode_index = 0

    running = True
    paused = False
    show_debug = settings["debug_default"]
    pygame.mouse.set_visible(False)

    # Welcome message timer
    welcome_msg = welcome_texts.get(current_lang, "").format(name=username)
    welcome_timer = 180  # ~3 seconds

    while running:
        dt = clock.tick(FPS) / 16.667
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
        quit_rect = pygame.Rect(
            resume_rect.x,
            resume_rect.bottom + 14,
            pause_button_width,
            pause_button_height,
        )

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif paused:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    paused = False
                    pygame.mouse.set_visible(False)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if resume_rect.collidepoint(event.pos):
                        paused = False
                        pygame.mouse.set_visible(False)
                    elif quit_rect.collidepoint(event.pos):
                        running = False

            elif event.type == pygame.VIDEORESIZE and not is_fullscreen:
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode(
                    (screen_width, screen_height),
                    pygame.RESIZABLE
                )

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = True
                    pygame.mouse.set_visible(True)
                    is_rmb_dragging = False
                elif event.key == pygame.K_F3:
                    show_debug = not show_debug
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
                elif event.key == pygame.K_TAB:
                    mode_index = (mode_index + 1) % len(mode_list)
                    game_mode = mode_list[mode_index]
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

            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    new_size = block_size * ZOOM_FACTOR
                    max_bs = max(min(screen_width, screen_height) / 2, DEFAULT_BLOCK_SIZE)
                    if new_size <= max_bs:
                        block_size = int(new_size)
                elif event.y < 0:
                    new_size = block_size / ZOOM_FACTOR
                    if new_size >= MIN_BLOCK_SIZE:
                        block_size = max(int(new_size), MIN_BLOCK_SIZE)

        # Right mouse drag
        if not paused:
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

        if not paused:
            player.update(keys, dt)
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
        cx_off = screen_width // 2
        cy_off = screen_height // 2
        world_mx = camera_x + (mx - cx_off) / block_size
        world_my = camera_y - (my - cy_off) / block_size
        wx = int(math.floor(world_mx))
        wy = int(math.ceil(world_my))
        if not paused and world_my >= 1:
            bt = world.get_block(wx, wy)
            if bt:
                hovered_block = bt
                hovered_wx = wx
                hovered_wy = wy
                hovered_sx = int((wx - camera_x) * block_size + cx_off)
                hovered_sy = int((camera_y - wy) * block_size + cy_off)

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

        # Custom cursor
        if not paused:
            cursor_key = "mouse_right_spectator" if is_rmb_dragging else "mouse"
            cursor_img = gui_textures.get(cursor_key)
            if cursor_img:
                screen.blit(cursor_img, (mx, my))

        # Mode label
        mode_name = mode_texts.get(current_lang, "Spectator")
        mode_surf = mode_font.render(mode_name, True, (255, 255, 255))
        mode_shadow = mode_font.render(mode_name, True, (0, 0, 0))
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
            lines = [
                tref("debug_fps", fps=clock.get_fps()),
                tref("debug_mode", mode=mode_name),
                tref("debug_player", x=px, y=py),
                tref("debug_camera", x=camera_x, y=camera_y),
                tref("debug_mouse", mx=mx, my=my, wx=wx, wy=wy) + hover_debug,
                tref("debug_zoom", pct=zoom_pct),
                tref("debug_window", w=screen_width, h=screen_height) +
                (tref("debug_fullscreen") if is_fullscreen else ""),
                tref("debug_chunks", n=len(world.chunks)),
                tref("debug_textures", n=len(textures)),
                tref("debug_lang"),
                controls_texts.get(current_lang, ""),
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
                (quit_rect, pause_text("pause_quit", "Quit")),
            ):
                hovered = rect.collidepoint((mx, my))
                color = (70, 70, 70) if hovered else (50, 50, 50)
                pygame.draw.rect(screen, color, rect, border_radius=6)
                pygame.draw.rect(screen, (100, 200, 255), rect, 2, border_radius=6)
                label_surf = pause_button_font.render(label, True, (255, 255, 255))
                screen.blit(label_surf, label_surf.get_rect(center=rect.center))

        pygame.display.flip()

    return False  # Signal to quit


def main():
    """Main entry point: show homepage, then start game."""
    pygame.init()

    screen_width = INITIAL_WIDTH
    screen_height = INITIAL_HEIGHT

    screen = pygame.display.set_mode(
        (screen_width, screen_height),
        pygame.RESIZABLE
    )
    pygame.display.set_caption("My2DWorld")

    # Show homepage → returns (username, lang, settings, screen_width, screen_height) or None
    result = homepage(screen, screen_width, screen_height)

    if result is None:
        # User quit from homepage
        pygame.quit()
        sys.exit()

    username, lang, settings, actual_width, actual_height = result

    # Start the game with actual screen dimensions (fixes maximize/fullscreen scaling)
    start_game(screen, actual_width, actual_height, username, lang, settings)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
