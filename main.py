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

# Constants
INITIAL_WIDTH = 1024
INITIAL_HEIGHT = 768
DEFAULT_BLOCK_SIZE = 32  # pixels per block (default = max zoom out)
MIN_BLOCK_SIZE = 32      # cannot zoom out further than default
FPS = 60
VIEW_DISTANCE_CHUNKS = 8  # chunks loaded in each direction

# Zoom limits
ZOOM_FACTOR = 1.15

# Highlight color for hovered block
HIGHLIGHT_COLOR = (255, 255, 255)  # white
HIGHLIGHT_WIDTH = 2

# Config paths
FONT_PATH = "fonts/LXGWWenKai-Regular.ttf"
BLOCK_CONFIG_PATH = "config/block.json"
TRANSLATE_CONFIG_PATH = "config/translate.json"

# GUIs path
GUI_DIR = "image/gui"


class GameMode:
    """Game mode enum-like class."""
    SPECTATOR = "spectator"


def load_json(path: str):
    """Load a JSON file and return its contents."""
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
    """Load all block textures at original size from the image directory."""
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
    """Get a texture scaled to block_size, or create a colored fallback."""
    if block_type in textures:
        raw = textures[block_type]
        return pygame.transform.scale(raw, (block_size, block_size))

    # Create a fallback colored surface
    info = color_map.get(block_type, {})
    color = info.get("color", [200, 0, 200]) if isinstance(info, dict) else (200, 0, 200)
    surf = pygame.Surface((block_size, block_size))
    surf.fill(color)
    pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), 1)
    return surf


def load_gui_textures() -> dict:
    """Load GUI textures (cursors)."""
    gui = {}
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


def main():
    """Main game entry point."""
    pygame.init()

    # Load configs
    print("Loading configs...")
    block_config = load_json(BLOCK_CONFIG_PATH)
    translate_config = load_json(TRANSLATE_CONFIG_PATH)
    print(f"  block.json: {len(block_config)} block types")
    print(f"  translate.json loaded")

    # Current language
    current_lang = translate_config.get("language", "zh")

    # Helper: translate a gui key
    def t(key, **kwargs):
        texts = translate_config.get("gui", {}).get(key, {})
        text = texts.get(current_lang, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        return text

    # Helper: translate a block name
    def block_name(block_type):
        entries = translate_config.get("blocks", {}).get(block_type, {})
        return entries.get(current_lang, block_type)

    # Build color map from block config
    color_map = {}
    for key, info in block_config.items():
        if isinstance(info, dict) and "color" in info:
            color_map[key] = info

    # GUI texts
    gui_section = translate_config.get("gui", {})
    window_title_texts = gui_section.get("window_title", {})
    mode_texts = gui_section.get("mode_spectator", {})
    controls_texts = gui_section.get("controls_hint", {})

    screen_width = INITIAL_WIDTH
    screen_height = INITIAL_HEIGHT
    is_fullscreen = False

    screen = pygame.display.set_mode(
        (screen_width, screen_height),
        pygame.RESIZABLE
    )
    pygame.display.set_caption(window_title_texts.get(current_lang, "My2DWorld"))
    clock = pygame.time.Clock()

    # Load font from file
    if os.path.isfile(FONT_PATH):
        debug_font = pygame.font.Font(FONT_PATH, 14)
        name_font = pygame.font.Font(FONT_PATH, 20)
        mode_font = pygame.font.Font(FONT_PATH, 18)
        print(f"  Loaded font: {FONT_PATH}")
    else:
        debug_font = pygame.font.SysFont("Arial", 14)
        name_font = pygame.font.SysFont("Arial", 20)
        mode_font = pygame.font.SysFont("Arial", 18)
        print(f"  Warning: font '{FONT_PATH}' not found, using Arial fallback")

    # Load textures
    print("Loading textures...")
    textures = load_textures()
    print(f"Loaded {len(textures)} textures")

    # Load GUI textures
    print("Loading GUI...")
    gui_textures = load_gui_textures()

    # Create world and player
    world = World(view_distance_chunks=VIEW_DISTANCE_CHUNKS)
    start_surface = world.get_surface_height(0)
    player = Player(start_x=0, start_y=start_surface + 3)

    # Initial view update based on player start position
    world.update_view(player.x)

    # Zoom state
    block_size = DEFAULT_BLOCK_SIZE

    # Camera pan (right mouse drag)
    camera_offset_x = 0.0
    camera_offset_y = 0.0
    is_rmb_dragging = False
    rmb_drag_start_mouse = (0, 0)   # screen coords
    rmb_drag_start_offset = (0.0, 0.0)  # world coords

    # Game mode
    game_mode = GameMode.SPECTATOR
    mode_list = [GameMode.SPECTATOR]
    mode_index = 0

    running = True
    show_debug = True

    # Hide system mouse cursor (we draw our own)
    pygame.mouse.set_visible(False)

    while running:
        dt = clock.tick(FPS) / 16.667  # normalize to ~60 FPS
        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()
        mx, my = pygame.mouse.get_pos()

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE and not is_fullscreen:
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode(
                    (screen_width, screen_height),
                    pygame.RESIZABLE
                )

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    show_debug = not show_debug
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode(
                            (0, 0),
                            pygame.FULLSCREEN
                        )
                        screen_width, screen_height = screen.get_size()
                    else:
                        screen_width = INITIAL_WIDTH
                        screen_height = INITIAL_HEIGHT
                        screen = pygame.display.set_mode(
                            (screen_width, screen_height),
                            pygame.RESIZABLE
                        )
                elif event.key == pygame.K_TAB:
                    # Cycle game mode (currently only spectator)
                    mode_index = (mode_index + 1) % len(mode_list)
                    game_mode = mode_list[mode_index]
                elif event.key == pygame.K_l:
                    # Toggle language
                    current_lang = "en" if current_lang == "zh" else "zh"
                    pygame.display.set_caption(
                        window_title_texts.get(current_lang, "My2DWorld")
                    )

            elif event.type == pygame.MOUSEWHEEL:
                # Zoom in/out
                if event.y > 0:
                    new_size = block_size * ZOOM_FACTOR
                    max_bs = max(min(screen_width, screen_height) / 2, DEFAULT_BLOCK_SIZE)
                    if new_size <= max_bs:
                        block_size = int(new_size)
                elif event.y < 0:
                    new_size = block_size / ZOOM_FACTOR
                    if new_size >= MIN_BLOCK_SIZE:
                        block_size = max(int(new_size), MIN_BLOCK_SIZE)

        # --- Right mouse button drag to pan camera (spectator mode) ---
        if mouse_buttons[2]:  # right button pressed
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

        # Update player
        player.update(keys, dt)
        px, py = player.get_pos()

        # Update world view based on player/camera position
        adjusted_cam_x = px + camera_offset_x
        world.update_view(adjusted_cam_x)

        # Camera follows player with offset
        camera_x = adjusted_cam_x
        camera_y = py + camera_offset_y

        # --- Calculate hovered block under mouse ---
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
        if world_my >= 1:
            bt = world.get_block(wx, wy)
            if bt:
                hovered_block = bt
                hovered_wx = wx
                hovered_wy = wy
                hovered_sx = int((wx - camera_x) * block_size + cx_off)
                hovered_sy = int((camera_y - wy) * block_size + cy_off)

        # --- RENDER ---
        screen.fill((135, 206, 235))  # sky blue

        # Render blocks
        def draw_block(sx, sy, block_type):
            tex = get_texture_or_fallback(textures, block_type, block_size, color_map)
            screen.blit(tex, (sx, sy))

        world.render_blocks(
            camera_x, camera_y,
            screen_width, screen_height,
            block_size,
            draw_block
        )

        # Draw highlight border on hovered block
        if hovered_block:
            pygame.draw.rect(
                screen, HIGHLIGHT_COLOR,
                (hovered_sx, hovered_sy, block_size, block_size),
                HIGHLIGHT_WIDTH
            )

        # Draw block name at top-center of screen
        if hovered_block:
            name = block_name(hovered_block)
            name_surf = name_font.render(name, True, (255, 255, 255))
            shadow_surf = name_font.render(name, True, (0, 0, 0))
            nx = (screen_width - name_surf.get_width()) // 2
            ny = 10
            screen.blit(shadow_surf, (nx + 1, ny + 1))
            screen.blit(name_surf, (nx, ny))

        # Draw custom mouse cursor
        cursor_key = "mouse_right_spectator" if is_rmb_dragging else "mouse"
        cursor_img = gui_textures.get(cursor_key)
        if cursor_img:
            screen.blit(cursor_img, (mx, my))

        # Draw mode label at bottom-right corner
        mode_name = mode_texts.get(current_lang, "Spectator")
        mode_surf = mode_font.render(mode_name, True, (255, 255, 255))
        mode_shadow = mode_font.render(mode_name, True, (0, 0, 0))
        mode_x = screen_width - mode_surf.get_width() - 10
        mode_y = screen_height - mode_surf.get_height() - 10
        screen.blit(mode_shadow, (mode_x + 1, mode_y + 1))
        screen.blit(mode_surf, (mode_x, mode_y))

        # Debug info
        if show_debug:
            zoom_pct = int(block_size / DEFAULT_BLOCK_SIZE * 100)
            hover_debug = ""
            if hovered_block:
                name = block_name(hovered_block)
                hover_debug = t("debug_hover", name=name)
            lines = [
                t("debug_fps", fps=clock.get_fps()),
                t("debug_mode", mode=mode_name),
                t("debug_player", x=px, y=py),
                t("debug_camera", x=camera_x, y=camera_y),
                t("debug_mouse", mx=mx, my=my, wx=wx, wy=wy) + hover_debug,
                t("debug_zoom", pct=zoom_pct),
                t("debug_window", w=screen_width, h=screen_height) +
                (t("debug_fullscreen") if is_fullscreen else ""),
                t("debug_chunks", n=len(world.chunks)),
                t("debug_textures", n=len(textures)),
                t("debug_lang"),
                controls_texts.get(current_lang,
                    "WASD:Move | Scroll:Zoom | RMB:Pan | L:Lang | F3:Debug | F11:FS | ESC:Exit"),
            ]
            for i, line in enumerate(lines):
                text_surf = debug_font.render(line, True, (255, 255, 255))
                shadow = debug_font.render(line, True, (0, 0, 0))
                screen.blit(shadow, (11, 11 + i * 18))
                screen.blit(text_surf, (10, 10 + i * 18))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()