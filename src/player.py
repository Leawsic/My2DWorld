"""
Player entity with physics, collision, textures, and animation.

Movement (creative mode):
- A/D horizontal movement
- Space = jump (supports double jump)
- Hold space for 3 seconds = toggle flying
- Flying: WASD moves freely, no gravity, faster
"""

import math
import os

import pygame

from runtime import PROJECT_ROOT

# ---------------------------------------------------------------------------
# Player configuration
# ---------------------------------------------------------------------------
WALK_SPEED = 1.8            # horizontal walk speed (blocks/sec)
FLY_SPEED = 3.5             # flying speed (blocks/sec)
JUMP_VELOCITY = 9.5         # initial upward velocity for a jump (blocks/sec)
MAX_JUMPS = 2               # double jump support
GRAVITY = 14.0              # downward acceleration (blocks/sec²)
FLY_HOLD_TIME = 3.0         # seconds of holding space to toggle flying

# Collision box (relative to the player's feet).
# Width: 0.5 blocks, height: 1.9 blocks. ``y`` is the foot coordinate.
BODY_HALF_WIDTH = 0.25      # half the width (0.5 total)
BODY_HEIGHT = 1.9           # total height in blocks
BODY_HALF_HEIGHT = BODY_HEIGHT / 2
BODY_FOOT_OFFSET = BODY_HALF_HEIGHT  # compatibility for old callers

# Player textures
PLAYER_TEXTURE_DIR = os.path.join(PROJECT_ROOT, "image", "player")
STEVE_STAND_PATH = os.path.join(PLAYER_TEXTURE_DIR, "steve/stand/1.png")
STEVE_MOVE_DIR = os.path.join(PLAYER_TEXTURE_DIR, "steve/move")

MOVE_ANIM_FPS = 10          # animation frames per second
MOVE_ANIM_INTERVAL = 1.0 / MOVE_ANIM_FPS


def load_player_textures():
    """Load all player textures. Returns a dict with 'stand' and 'move' lists."""
    tex = {"stand": [], "move": []}
    try:
        img = pygame.image.load(STEVE_STAND_PATH).convert_alpha()
        tex["stand"] = [img]
    except Exception:
        pass

    if os.path.isdir(STEVE_MOVE_DIR):
        frames = []
        for fname in sorted(os.listdir(STEVE_MOVE_DIR)):
            if fname.lower().endswith(".png"):
                try:
                    frames.append(pygame.image.load(
                        os.path.join(STEVE_MOVE_DIR, fname)).convert_alpha())
                except Exception:
                    continue
        if frames:
            tex["move"] = frames
    return tex


class Player:
    """
    Player with physics state. Position (x, y) is the player's feet.
    World Y increases upward.
    """

    def __init__(self, start_x: float = 0, start_y: float = 50):
        self.x = float(start_x)
        self.y = float(start_y)

        # Physics state
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.on_ground = False
        self.jumps_used = 0
        self.flying = False
        self.fly_hold_timer = 0.0      # seconds holding space to trigger fly toggle
        self.fly_toggled = False       # prevents re-toggling while still holding
        self.space_was_down = False    # for jump edge detection

        # Animation state
        self.textures = load_player_textures()
        self.anim_state = "stand"      # "stand" or "move"
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.facing = 1                # 1 = right, -1 = left

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, keys, dt, world):
        """
        Update player physics and animation.
        dt is normalized: 1.0 at 60fps = 1/60 real seconds per unit.
        world is the World instance (used for collision detection).
        """
        dt_sec = dt / 60.0  # real seconds

        self._handle_fly_toggle(keys, dt_sec)

        # Horizontal input
        self.velocity_x = 0.0
        moving_horizontal = False
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.velocity_x = -WALK_SPEED
            self.facing = -1
            moving_horizontal = True
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.velocity_x = WALK_SPEED
            self.facing = 1
            moving_horizontal = True

        if self.flying:
            self._update_flying(keys)
        else:
            self._update_grounded(keys)

        # Apply movement with collision in X and Y separately (using real seconds)
        self._move_and_collide_x(world, dt_sec)
        self._move_and_collide_y(world, dt_sec)

        # Update animation state
        self._update_animation(dt_sec)

    def get_pos(self):
        """Get (x, y) foot position."""
        return self.x, self.y

    def get_collision_rect(self):
        """
        Return world-space collision rectangle as (left, bottom, width, height).
        The bottom of the box is exactly at ``self.y``.
        """
        left = self.x - BODY_HALF_WIDTH
        bottom = self.y
        return left, bottom, BODY_HALF_WIDTH * 2, BODY_HEIGHT

    def reset(self, start_x=0, start_y=50):
        """Reset player to a given position with fresh state."""
        self.x = float(start_x)
        self.y = float(start_y)
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.on_ground = False
        self.jumps_used = 0
        self.flying = False
        self.fly_hold_timer = 0.0
        self.fly_toggled = False
        self.space_was_down = False
        self.anim_state = "stand"
        self.anim_frame = 0
        self.anim_timer = 0.0

    # ------------------------------------------------------------------
    # Texture & rendering
    # ------------------------------------------------------------------
    def get_current_frame(self):
        """Return the correct texture for the current animation state."""
        frames = self.textures.get(self.anim_state, [])
        if not frames:
            return None
        idx = self.anim_frame % len(frames)
        return frames[idx]

    def render(self, screen, camera_x, camera_y, block_size):
        """Draw the player with its bottom aligned to its foot position."""
        frame = self.get_current_frame()
        if frame is None:
            return
        # Scale to the collision-box height and align the image bottom with feet.
        target_h = block_size * BODY_HEIGHT
        fw, fh = frame.get_size()
        if fw <= 0 or fh <= 0:
            return
        scale = target_h / fh
        scaled_w = max(1, int(fw * scale))
        scaled_h = max(1, int(fh * scale))
        img = pygame.transform.scale(frame, (scaled_w, scaled_h))

        # Flip horizontally if facing left
        if self.facing < 0:
            img = pygame.transform.flip(img, True, False)

        cx_off = screen.get_width() // 2
        cy_off = screen.get_height() // 2
        sx = int((self.x - camera_x) * block_size + cx_off)
        foot_sy = int((camera_y - self.y) * block_size + cy_off)

        screen.blit(img, (sx - scaled_w // 2, foot_sy - scaled_h))

    # ------------------------------------------------------------------
    # Physics helpers
    # ------------------------------------------------------------------
    def _handle_fly_toggle(self, keys, dt_sec):
        """Hold space for FLY_HOLD_TIME seconds to toggle flying."""
        space_down = keys[pygame.K_SPACE]
        if space_down:
            self.fly_hold_timer += dt_sec
            if self.fly_hold_timer >= FLY_HOLD_TIME and not self.fly_toggled:
                self.flying = not self.flying
                self.fly_toggled = True
                self.velocity_y = 0.0
                self.jumps_used = 0
        else:
            self.fly_hold_timer = 0.0
            self.fly_toggled = False

    def _update_flying(self, keys):
        """Flying movement: no gravity, free WASD, faster speed."""
        # Horizontal velocity already set in update(); only set vertical here.
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.velocity_y = FLY_SPEED
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.velocity_y = -FLY_SPEED
        else:
            self.velocity_y = 0.0
        # Track space edge state so returning to ground does not auto-jump.
        self.space_was_down = keys[pygame.K_SPACE]

    def _update_grounded(self, keys):
        """Gravity + jump handling (non-flying)."""
        # Jump on space press edge (not simple hold).
        space_down = keys[pygame.K_SPACE]
        if space_down and not self.space_was_down and self.fly_hold_timer < 0.05:
            self._try_jump()
        self.space_was_down = space_down

    def _try_jump(self):
        """Attempt a jump if jumps remain (ground jump + air jump = double jump)."""
        if self.jumps_used < MAX_JUMPS:
            self.velocity_y = JUMP_VELOCITY
            self.jumps_used += 1
            self.on_ground = False

    def _move_and_collide_x(self, world, dt_sec):
        """Move horizontally and resolve collisions against solid blocks."""
        dx = self.velocity_x * dt_sec
        self.x += dx

        left, bottom, width, height = self.get_collision_rect()
        top = bottom + height
        # World block ``y`` is its top edge, so block y occupies [y - 1, y].
        # Convert the player's continuous vertical span to those block indices.
        y_start = int(math.floor(bottom)) + 1
        y_end = int(math.ceil(top))

        if dx > 0:  # moving right
            # Right edge entered a block at column floor(left + width)
            fx = math.floor(left + width)
            for wy in range(y_start, y_end + 1):
                if world.get_block(fx, wy):
                    # Push back so right edge is just left of block fx
                    self.x = fx - BODY_HALF_WIDTH - 0.001
                    self.velocity_x = 0.0
                    break
        elif dx < 0:  # moving left
            # Left edge entered a block at column floor(left)
            fx = math.floor(left)
            for wy in range(y_start, y_end + 1):
                if world.get_block(fx, wy):
                    # Push right so left edge is just right of block fx
                    self.x = fx + 1 + BODY_HALF_WIDTH + 0.001
                    self.velocity_x = 0.0
                    break

    def _move_and_collide_y(self, world, dt_sec):
        """Move vertically and resolve collisions with ground/ceiling."""
        if self.flying:
            dy = self.velocity_y * dt_sec
            self.y += dy
            self.on_ground = False
            # Simple collision while flying
            left, bottom, width, height = self.get_collision_rect()
            top = bottom + height
            x_start = int(math.floor(left))
            x_end = int(math.floor(left + width))
            if x_end < x_start:
                x_end = x_start
            if dy > 0:  # moving up
                fy = int(math.ceil(top))
                for wx in range(x_start, x_end + 1):
                    if world.get_block(wx, fy):
                        # Place player top just below the ceiling block
                        self.y = fy - 0.001 - height
                        self.velocity_y = 0.0
                        break
            elif dy < 0:  # moving down
                fy = int(math.ceil(bottom))
                for wx in range(x_start, x_end + 1):
                    if world.get_block(wx, fy):
                        self.y = fy + 0.001
                        self.velocity_y = 0.0
                        break
            return

        # Apply gravity (velocity decreases over real time)
        self.velocity_y -= GRAVITY * dt_sec

        dy = self.velocity_y * dt_sec
        self.y += dy
        left, bottom, width, height = self.get_collision_rect()
        top = bottom + height
        x_start = int(math.floor(left))
        x_end = int(math.floor(left + width))
        if x_end < x_start:
            x_end = x_start

        if dy < 0:  # moving down (falling)
            # Block y occupies [y - 1, y], so feet enter row ceil(bottom).
            fy = int(math.ceil(bottom))
            landed = False
            for wx in range(x_start, x_end + 1):
                if world.get_block(wx, fy):
                    # Standing on top of block fy: feet at fy.
                    self.y = fy + 0.001
                    self.velocity_y = 0.0
                    self.on_ground = True
                    self.jumps_used = 0
                    landed = True
                    break
            if not landed:
                self.on_ground = False
        else:  # moving up
            # The head enters a block whose top-edge coordinate is ceil(top).
            fy = int(math.ceil(top))
            for wx in range(x_start, x_end + 1):
                if world.get_block(wx, fy):
                    # Head just below block fy: top at fy - 0.001
                    self.y = fy - 0.001 - height
                    self.velocity_y = 0.0
                    break

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------
    def _update_animation(self, dt_sec):
        """Advance animation state based on actual movement (velocity)."""
        moving = False
        if self.flying:
            # In flight: animate only when moving horizontally.
            # Vertical-only movement (W/S) keeps the stand frame.
            moving = (abs(self.velocity_x) > 0.05)
        else:
            # Grounded: animate only when walking horizontally on ground.
            if self.on_ground and abs(self.velocity_x) > 0.05:
                moving = True
            elif self.on_ground:
                # Standing still on ground.
                moving = False
            else:
                # In the air (jumping/falling): use stand frames.
                moving = False

        if moving:
            self._set_move_anim(dt_sec)
        else:
            self.anim_state = "stand"
            self.anim_frame = 0
            self.anim_timer = 0.0

    def _set_move_anim(self, dt_sec):
        """Switch to/advance move animation, always starting from frame 0."""
        if self.anim_state != "move":
            self.anim_state = "move"
            self.anim_frame = 0
            self.anim_timer = 0.0
        else:
            self.anim_timer += dt_sec
            if self.anim_timer >= MOVE_ANIM_INTERVAL:
                # Move to next frame, looping
                self.anim_frame = (self.anim_frame + 1) % max(1, len(self.textures.get("move", [])))
                self.anim_timer -= MOVE_ANIM_INTERVAL
