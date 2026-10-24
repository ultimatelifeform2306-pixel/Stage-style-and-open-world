"""
QUAY KINGS - a 2D versus fighting game made with pygame.

Grown out of the "2D Fighting Game Sandbox Engine": same Fighter class,
same 800x480 stage, same health bars - now with rounds, a round timer,
punches and kicks, crouching and jumping attacks, blocking, fireballs,
a super move, combos, hit effects and a CPU opponent.

Run:
    pip install pygame
    python quay_kings.py

Controls
    Player 1:  A / D move   W jump   S crouch
               F punch   G kick   H fireball   R super (when POWER is MAX)
    Player 2:  Arrow keys move / jump / crouch
               Numpad 1 or ,  punch     Numpad 2 or .  kick
               Numpad 3 or /  fireball  Numpad 0 or Right Shift  super
    Hold BACK (away from the opponent) to block. Crouch-block stops sweeps,
    stand-block stops jump-ins. Land a punch or kick, then press fireball
    or super straight away to cancel it into a combo.
    ESC / P pause    F1 show hitboxes
"""
import math
import random
import sys

import pygame

# --- GAME CONFIGURATION ---
WIDTH, HEIGHT = 800, 480
FPS = 60
GROUND_Y = HEIGHT - 80
GRAVITY = 1.0
STAGE_LEFT, STAGE_RIGHT = 20, WIDTH - 20
ROUND_TIME = 99            # seconds per round
ROUNDS_TO_WIN = 2          # best of three
MAX_HEALTH = 100
MAX_METER = 100

BODY_W = 60
STAND_H, CROUCH_H, JUMP_H, LYING_H = 110, 70, 90, 24
LEFT_LIMIT = STAGE_LEFT + BODY_W / 2
RIGHT_LIMIT = STAGE_RIGHT - BODY_W / 2

# --- COLOR PALETTE ---
WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
DARK   = (20, 20, 30)
RED    = (220, 50, 50)
BLUE   = (50, 100, 240)
YELLOW = (240, 200, 30)
GREEN  = (50, 200, 100)
ORANGE = (255, 140, 40)
CYAN   = (80, 220, 255)
SKIN   = (236, 188, 140)

CHARACTERS = {
    "KAI":  dict(gi=BLUE, trim=WHITE, band=RED, hair=(30, 25, 25), ki=CYAN),
    "ROSA": dict(gi=RED, trim=YELLOW, band=WHITE, hair=(110, 50, 25), ki=ORANGE),
}

# Frame data: startup -> active -> recovery. "reach" is measured from the body
# edge, "y" is the hitbox offset from the top of the attacker's body.
# hit: "high" must be blocked standing, "low" must be blocked crouching.
MOVES = {
    "punch":   dict(startup=4, active=4,  recovery=9,  damage=6,  reach=46, h=22, y=18,
                    hitstun=16, blockstun=10, push=4, hit="mid"),
    "kick":    dict(startup=7, active=5,  recovery=15, damage=9,  reach=64, h=26, y=38,
                    hitstun=19, blockstun=12, push=6, hit="mid"),
    "c_punch": dict(startup=4, active=4,  recovery=9,  damage=5,  reach=44, h=20, y=14,
                    hitstun=15, blockstun=9,  push=4, hit="mid"),
    "c_kick":  dict(startup=8, active=6,  recovery=18, damage=8,  reach=66, h=18, y=50,
                    hitstun=0,  blockstun=12, push=5, hit="low", knockdown=True),
    "j_punch": dict(startup=5, active=8,  recovery=6,  damage=8,  reach=40, h=30, y=30,
                    hitstun=18, blockstun=10, push=4, hit="high"),
    "j_kick":  dict(startup=6, active=10, recovery=6,  damage=10, reach=50, h=34, y=56,
                    hitstun=20, blockstun=12, push=5, hit="high"),
}
CANCELLABLE = ("punch", "kick", "c_punch", "c_kick")
FIREBALL_HIT = dict(damage=10, chip=2, hitstun=20, blockstun=14, push=6, hit="mid")
SUPER_HIT = dict(damage=28, chip=6, hitstun=0, blockstun=20, push=9, hit="mid", knockdown=True)
SPECIAL_FRAMES = {False: (12, 22), True: (16, 28)}   # (startup, recovery)
ACTIONABLE = ("idle", "walk", "crouch", "jump")

# --- CONTROLS ---
ACTIONS = ("left", "right", "up", "down", "punch", "kick", "special", "super")
NEUTRAL = {a: False for a in ACTIONS}
P1_KEYS = {"left": [pygame.K_a], "right": [pygame.K_d], "up": [pygame.K_w], "down": [pygame.K_s],
           "punch": [pygame.K_f], "kick": [pygame.K_g], "special": [pygame.K_h], "super": [pygame.K_r]}
P2_KEYS = {"left": [pygame.K_LEFT], "right": [pygame.K_RIGHT], "up": [pygame.K_UP], "down": [pygame.K_DOWN],
           "punch": [pygame.K_KP1, pygame.K_COMMA], "kick": [pygame.K_KP2, pygame.K_PERIOD],
           "special": [pygame.K_KP3, pygame.K_SLASH], "super": [pygame.K_KP0, pygame.K_RSHIFT]}


def shade(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color)


def draw_text(surface, font, text, color, outline=2, **pos):
    base = font.render(text, True, color)
    edge = font.render(text, True, BLACK)
    rect = base.get_rect(**pos)
    for dx in (-outline, 0, outline):
        for dy in (-outline, 0, outline):
            if dx or dy:
                surface.blit(edge, rect.move(dx, dy))
    surface.blit(base, rect)
    return rect


def limb(surface, color, a, b, width):
    """A thick, outlined, round-ended line: the building block of every fighter."""
    pygame.draw.line(surface, BLACK, a, b, width + 4)
    pygame.draw.circle(surface, BLACK, a, width // 2 + 2)
    pygame.draw.circle(surface, BLACK, b, width // 2 + 2)
    pygame.draw.line(surface, color, a, b, width)
    pygame.draw.circle(surface, color, a, width // 2)
    pygame.draw.circle(surface, color, b, width // 2)


# --- POSES --- (x is toward the opponent, y is up from the feet)
def stand_pose(b=0.0):
    return dict(hip=(0, -55 + b), neck=(4, -95 + b), head=(7, -106 + b),
                fk=(14, -28), ff=(20, 0), bk=(-10, -28), bf=(-18, 0),
                fe=(22, -78 + b), fh=(32, -90 + b), be=(12, -70 + b), bh=(26, -82 + b))


def crouch_pose():
    return dict(hip=(0, -32), neck=(10, -62), head=(15, -73),
                fk=(24, -24), ff=(22, 0), bk=(-12, -16), bf=(-24, 0),
                fe=(26, -50), fh=(34, -62), be=(16, -44), bh=(28, -56))


def jump_pose():
    return dict(hip=(0, -58), neck=(4, -96), head=(6, -107),
                fk=(18, -46), ff=(10, -26), bk=(-4, -42), bf=(-16, -28),
                fe=(20, -80), fh=(30, -92), be=(10, -72), bh=(24, -84))


LYING_POSE = dict(hip=(-8, -10), neck=(-46, -12), head=(-60, -12),
                  fk=(12, -18), ff=(32, -6), bk=(10, -10), bf=(30, -4),
                  fe=(-34, -24), fh=(-20, -10), be=(-50, -8), bh=(-64, -4))


class Fighter(pygame.sprite.Sprite):
    def __init__(self, name, x, facing, controller):
        super().__init__()
        self.name = name
        self.look = CHARACTERS[name]
        self.controller = controller
        self.start_x, self.start_facing = x, facing
        self.wins = 0
        self.meter = 0
        self.reset()

    def reset(self):
        # Physics
        self.x, self.y = float(self.start_x), float(GROUND_Y)
        self.vel_x = self.vel_y = 0.0
        self.facing = self.start_facing
        self.on_ground = True
        self.air_attacked = False
        # Combat
        self.health = MAX_HEALTH
        self.shown_health = MAX_HEALTH      # trails behind health for the red damage bar
        self.state = "idle"
        self.timer = 0
        self.move = None
        self.move_frame = 0
        self.has_hit = False
        self.special_super = False
        self.holding_back = self.holding_down = False
        self.crouch_block = False
        self.invuln = 0
        self.flash = 0
        self.combo = 0
        self.anim_t = 0

    # --- body ---
    @property
    def crouching(self):
        return (self.state == "crouch"
                or (self.state == "attack" and self.move.startswith("c_"))
                or (self.state in ("blockstun", "hitstun") and self.crouch_block))

    @property
    def height(self):
        if self.state in ("knockdown", "ko") and self.on_ground:
            return LYING_H
        if self.crouching:
            return CROUCH_H
        return STAND_H if self.on_ground else JUMP_H

    @property
    def rect(self):
        h = self.height
        return pygame.Rect(int(self.x - BODY_W / 2), int(self.y - h), BODY_W, h)

    def clamp(self):
        self.x = max(LEFT_LIMIT, min(RIGHT_LIMIT, self.x))

    # --- input ---
    def handle_input(self, held, pressed, opponent, game):
        self.holding_back = held["left"] if self.facing == 1 else held["right"]
        self.holding_down = held["down"]

        # A punch or kick that connected can be cancelled into a special
        if (self.state == "attack" and self.has_hit and self.on_ground
                and self.move in CANCELLABLE and self.try_special(pressed, game)):
            return
        if self.state not in ACTIONABLE:
            return

        if not self.on_ground:
            if not self.air_attacked:
                if "punch" in pressed:
                    self.execute_attack("j_punch")
                elif "kick" in pressed:
                    self.execute_attack("j_kick")
            return

        if self.try_special(pressed, game):
            return
        if "punch" in pressed:
            self.execute_attack("c_punch" if held["down"] else "punch")
            return
        if "kick" in pressed:
            self.execute_attack("c_kick" if held["down"] else "kick")
            return

        # Jump execution
        if held["up"]:
            self.vel_y = -17
            self.vel_x = 4.5 * (held["right"] - held["left"])
            self.on_ground = False
            self.air_attacked = False
            self.state = "jump"
            return
        # Crouch logic
        if held["down"]:
            self.state = "crouch"
            self.vel_x = 0
            return
        # Left / Right movement (walking backward is slower)
        d = held["right"] - held["left"]
        self.vel_x = d * (4.2 if d == self.facing else 3.2)
        self.state = "walk" if d else "idle"

    def try_special(self, pressed, game):
        if "super" in pressed and self.meter >= MAX_METER:
            self.meter = 0
            self.begin_special(True)
            game.super_freeze(self)
            return True
        if "special" in pressed and not any(p.owner is self for p in game.projectiles):
            self.begin_special(False)
            return True
        return False

    def begin_special(self, is_super):
        self.state = "special"
        self.move_frame = 0
        self.special_super = is_super
        self.vel_x = 0

    def execute_attack(self, name):
        self.state = "attack"
        self.move = name
        self.move_frame = 0
        self.has_hit = False
        if name.startswith("j_"):
            self.air_attacked = True
        else:
            self.vel_x = 0

    def attack_box(self):
        """The hitbox of the current attack, only while its active frames run."""
        if self.state != "attack" or self.has_hit:
            return None
        m = MOVES[self.move]
        if not m["startup"] <= self.move_frame < m["startup"] + m["active"]:
            return None
        r = self.rect
        w = BODY_W // 2 + m["reach"]
        left = r.centerx if self.facing == 1 else r.centerx - w
        return pygame.Rect(left, r.top + m["y"], w, m["h"])

    # --- getting hit ---
    def is_blocking(self, hit):
        if not self.on_ground or self.state not in ("idle", "walk", "crouch", "blockstun"):
            return False
        if not self.holding_back:
            return False
        if hit == "low" and not self.holding_down:
            return False
        if hit == "high" and self.holding_down:
            return False
        return True

    def receive_hit(self, m, direction, attacker, game, pos):
        if self.state in ("knockdown", "ko") or self.invuln > 0:
            return
        heavy = m is SUPER_HIT

        if self.is_blocking(m["hit"]):
            self.health = max(0, self.health - m.get("chip", 0))
            self.crouch_block = self.holding_down
            self.state = "blockstun"
            self.timer = m["blockstun"]
            self.vel_x = direction * m["push"]
            self.meter = min(MAX_METER, self.meter + 4)
            attacker.meter = min(MAX_METER, attacker.meter + 2)
            if self.health <= 0:
                self.knock_down(direction)
            game.on_block(pos)
            return

        was_crouching = self.crouching
        self.combo = self.combo + 1 if self.state == "hitstun" else 1
        self.health = max(0, self.health - m["damage"])
        self.flash = 5
        attacker.meter = min(MAX_METER, attacker.meter + m["damage"] * 1.2)
        self.meter = min(MAX_METER, self.meter + m["damage"] * 0.6)
        if self.health <= 0 or m.get("knockdown") or not self.on_ground:
            self.knock_down(direction)
        else:
            self.crouch_block = was_crouching
            self.state = "hitstun"
            self.timer = m["hitstun"]
            self.vel_x = direction * m["push"]
        game.on_hit(attacker, self, pos, heavy or self.health <= 0)

    def knock_down(self, direction):
        self.state = "knockdown"
        self.timer = 45
        self.vel_y = -9
        self.vel_x = direction * 4.5
        self.on_ground = False

    # --- per-frame ---
    def update(self, opponent, game):
        self.anim_t += 1
        if self.flash:
            self.flash -= 1
        if self.invuln:
            self.invuln -= 1
        if self.shown_health > self.health:
            self.shown_health = max(self.health, self.shown_health - 0.6)

        # Decrease active action countdowns
        if self.state == "attack":
            self.move_frame += 1
            m = MOVES[self.move]
            if self.move_frame >= m["startup"] + m["active"] + m["recovery"]:
                if not self.on_ground:
                    self.state = "jump"
                else:
                    self.state = "crouch" if self.holding_down else "idle"
        elif self.state == "special":
            self.move_frame += 1
            startup, recovery = SPECIAL_FRAMES[self.special_super]
            if self.move_frame == startup:
                game.projectiles.append(Projectile(self, self.special_super))
            if self.move_frame >= startup + recovery:
                self.state = "idle"
        elif self.state in ("hitstun", "blockstun"):
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.combo = 0
        elif self.state == "knockdown" and self.on_ground:
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.invuln = 30
                self.combo = 0

        # Apply Gravity
        if not self.on_ground:
            self.vel_y += GRAVITY
        self.x += self.vel_x
        self.y += self.vel_y

        # Keep on stage surface
        if self.y >= GROUND_Y:
            self.y = GROUND_Y
            if not self.on_ground:
                self.on_ground = True
                self.vel_y = 0
                if self.state == "knockdown":
                    self.vel_x = 0
                    game.shake(4)
                    if self.health <= 0:
                        self.state = "ko"
                elif self.state in ("jump", "attack"):   # landing ends air attacks
                    self.state = "idle"
                    self.vel_x = 0
        if self.on_ground and self.state in ("hitstun", "blockstun", "knockdown", "ko"):
            self.vel_x *= 0.82

        # Constrain inside boundaries
        self.clamp()
        if self.on_ground and self.state in ("idle", "walk", "crouch"):
            self.facing = 1 if opponent.x >= self.x else -1

    # --- drawing ---
    def get_pose(self):
        s, t = self.state, self.anim_t
        if s in ("knockdown", "ko") and self.on_ground:
            return dict(LYING_POSE)
        if s in ("hitstun", "knockdown"):
            p = crouch_pose() if s == "hitstun" and self.crouch_block else stand_pose()
            p.update(neck=(p["neck"][0] - 20, p["neck"][1] + 3), head=(p["head"][0] - 28, p["head"][1] + 4),
                     fe=(-4, p["neck"][1] + 20), fh=(10, p["neck"][1] + 30),
                     be=(-24, p["neck"][1] + 14), bh=(-34, p["neck"][1]))
            if s == "knockdown":
                p.update(fk=(12, -36), ff=(22, -20), bk=(-2, -30), bf=(4, -12))
            return p
        if s == "blockstun":
            if self.crouch_block:
                p = crouch_pose()
                p.update(fe=(18, -56), fh=(26, -70), be=(20, -48), bh=(30, -62))
            else:
                p = stand_pose()
                p.update(fe=(18, -84), fh=(26, -100), be=(16, -76), bh=(30, -90))
            return p
        if s == "attack":
            m = MOVES[self.move]
            f, st, ac, rc = self.move_frame, m["startup"], m["active"], m["recovery"]
            ext = f / st if f < st else (1.0 if f < st + ac else max(0.0, 1 - (f - st - ac) / rc))
            reach = m["reach"]
            if self.move == "punch":
                p = stand_pose()
                p.update(neck=(8 + 4 * ext, -95), head=(11 + 5 * ext, -106),
                         fe=(18 + ext * 22, -84), fh=(30 + ext * (reach - 4), -88))
            elif self.move == "kick":
                p = stand_pose()
                p.update(hip=(-2, -56), neck=(-10, -94), head=(-13, -105),
                         fk=(16 + ext * 14, -46 - ext * 16), ff=(20 + ext * (reach + 6), -24 - ext * 42),
                         bk=(-8, -28), bf=(-14, 0))
            elif self.move == "c_punch":
                p = crouch_pose()
                p.update(fe=(20 + ext * 16, -50), fh=(30 + ext * (reach - 4), -54))
            elif self.move == "c_kick":
                p = crouch_pose()
                p.update(neck=(2, -60), head=(4, -70), fk=(18 + ext * 18, -14),
                         ff=(22 + ext * (reach + 6), -4), bk=(-14, -18), bf=(-28, 0))
            elif self.move == "j_punch":
                p = jump_pose()
                p.update(fe=(18 + ext * 14, -74), fh=(28 + ext * (reach - 6), -66 + ext * 6))
            else:  # j_kick
                p = jump_pose()
                p.update(fk=(18 + ext * 10, -40), ff=(18 + ext * (reach + 4), -22 + ext * 8))
            return p
        if s == "special":
            startup = SPECIAL_FRAMES[self.special_super][0]
            p = stand_pose()
            p.update(hip=(-4, -50), neck=(6, -88), head=(10, -99),
                     fk=(18, -26), ff=(30, 0), bk=(-16, -24), bf=(-28, 0))
            if self.move_frame < startup:
                p.update(fe=(-6, -66), fh=(-14, -70), be=(-4, -62), bh=(-12, -66))
            else:
                p.update(fe=(22, -80), fh=(40, -80), be=(20, -74), bh=(38, -74))
            return p
        if s == "win":
            p = stand_pose()
            p.update(fe=(10, -118), fh=(14, -140), be=(-6, -76), bh=(-2, -58))
            return p
        if s == "jump":
            return jump_pose()
        if s == "crouch":
            return crouch_pose()
        if s == "walk":
            p = stand_pose()
            ph = t * 0.25
            sw = math.sin(ph) * 12
            p.update(fk=(4 + sw * 0.6, -28), ff=(6 + sw, -max(0.0, math.cos(ph)) * 6),
                     bk=(-4 - sw * 0.6, -28), bf=(-6 - sw, -max(0.0, -math.cos(ph)) * 6))
            return p
        return stand_pose(math.sin(t * 0.09) * 2)

    def draw_shadow(self, surface):
        lift = max(0, GROUND_Y - self.y)
        w = max(30, 76 - lift * 0.25)
        pygame.draw.ellipse(surface, (25, 20, 30), (self.x - w / 2, GROUND_Y - 6, w, 12))

    def draw(self, surface):
        f = self.facing
        flash = self.flash > 0
        gi = WHITE if flash else self.look["gi"]
        gi_dark = shade(gi, 0.7)
        skin = WHITE if flash else SKIN
        skin_dark = shade(skin, 0.82)
        trim = self.look["trim"]
        P = {k: (int(self.x + px * f), int(self.y + py)) for k, (px, py) in self.get_pose().items()}
        sh = (P["neck"][0], P["neck"][1] + 6)

        # back leg and arm
        limb(surface, gi_dark, P["hip"], P["bk"], 12)
        limb(surface, gi_dark, P["bk"], P["bf"], 10)
        limb(surface, skin_dark, P["bf"], (P["bf"][0] + 7 * f, P["bf"][1]), 6)
        limb(surface, skin_dark, sh, P["be"], 8)
        limb(surface, skin_dark, P["be"], P["bh"], 7)
        limb(surface, shade(trim, 0.8), P["bh"], P["bh"], 12)
        # torso + belt
        limb(surface, gi, P["hip"], P["neck"], 24)
        pygame.draw.line(surface, BLACK, (P["hip"][0] - 12, P["hip"][1] - 4), (P["hip"][0] + 12, P["hip"][1] - 4), 5)
        # front leg
        limb(surface, gi, P["hip"], P["fk"], 12)
        limb(surface, gi, P["fk"], P["ff"], 10)
        limb(surface, skin, P["ff"], (P["ff"][0] + 8 * f, P["ff"][1]), 6)
        # head: hair, face, eye, headband with tails
        hx, hy = P["head"]
        pygame.draw.circle(surface, BLACK, (hx, hy), 15)
        pygame.draw.circle(surface, self.look["hair"], (hx, hy), 13)
        pygame.draw.circle(surface, skin, (hx + 3 * f, hy + 3), 11)
        pygame.draw.circle(surface, BLACK, (hx + 8 * f, hy + 1), 2)
        band = self.look["band"]
        tail = math.sin(self.anim_t * 0.3) * 3
        pygame.draw.line(surface, band, (hx - 13 * f, hy - 4), (hx + 12 * f, hy - 7), 4)
        pygame.draw.line(surface, band, (hx - 12 * f, hy - 4), (hx - 26 * f, hy + 2 + tail), 3)
        pygame.draw.line(surface, band, (hx - 12 * f, hy - 4), (hx - 24 * f, hy + 8 - tail), 3)
        # front arm + glove
        limb(surface, skin, sh, P["fe"], 8)
        limb(surface, skin, P["fe"], P["fh"], 7)
        limb(surface, trim, P["fh"], P["fh"], 12)


class Projectile:
    def __init__(self, owner, is_super):
        self.owner = owner
        self.dir = owner.facing
        self.super = is_super
        self.x = owner.x + owner.facing * 48
        self.y = owner.y - 76
        self.speed = 9 if is_super else 6.5
        self.r = 26 if is_super else 15
        self.color = owner.look["ki"]
        self.alive = True
        self.t = 0

    @property
    def rect(self):
        s = int(self.r * 1.6)
        return pygame.Rect(int(self.x - s / 2), int(self.y - s / 2), s, s)

    def update(self):
        self.x += self.speed * self.dir
        self.t += 1
        if self.x < -60 or self.x > WIDTH + 60:
            self.alive = False

    def draw(self, surface):
        for i in range(4, 0, -1):
            pygame.draw.circle(surface, shade(self.color, 0.35 + 0.12 * (4 - i)),
                               (int(self.x - self.dir * i * 8), int(self.y)), int(self.r * (1 - i * 0.16)))
        wobble = math.sin(self.t * 0.5) * 2
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.r + wobble))
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), int(self.r * 0.55))


class KeyboardController:
    def __init__(self, mapping):
        self.mapping = mapping
        self.prev = dict(NEUTRAL)

    def read(self, keys, me, opponent, game):
        held = {a: any(keys[k] for k in codes) for a, codes in self.mapping.items()}
        pressed = {a for a in ACTIONS if held[a] and not self.prev[a]}
        self.prev = held
        return held, pressed


class CPUController:
    """A simple opponent: walks in, pokes, sweeps, jumps in, throws fireballs and blocks."""

    def __init__(self, skill=0.6):
        self.skill = skill
        self.plan = "wait"
        self.plan_t = 0
        self.cooldown = 0
        self.defend = None

    def read(self, keys, me, opp, game):
        held, pressed = dict(NEUTRAL), set()
        fwd = "right" if opp.x > me.x else "left"
        back = "left" if fwd == "right" else "right"
        dist = abs(opp.x - me.x)
        self.cooldown = max(0, self.cooldown - 1)

        # Defence: decide once per threat whether to block it
        threat = None
        if opp.state == "attack" and dist < 150:
            threat = MOVES[opp.move]["hit"]
        for p in game.projectiles:
            if p.owner is not me and (me.x - p.x) * p.dir > 0 and abs(p.x - me.x) < 200:
                threat = "mid"
        if threat and me.on_ground:
            if self.defend is None:
                self.defend = random.random() < self.skill
            if self.defend:
                held[back] = True
                held["down"] = threat == "low"
                return held, pressed
        elif not threat:
            self.defend = None

        # Combo: cancel a connected normal into a fireball
        if me.state == "attack" and me.has_hit and random.random() < 0.12 * self.skill:
            pressed.add("special")

        if self.plan_t <= 0:
            r = random.random()
            if dist > 280:
                self.plan = "fireball" if r < 0.35 else ("walk" if r < 0.85 else "jump")
            elif dist > 100:
                self.plan = "walk" if r < 0.6 else ("jump" if r < 0.8 else ("fireball" if r < 0.9 else "back"))
            else:
                self.plan = "attack" if r < 0.7 else ("back" if r < 0.85 else "wait")
            if me.meter >= MAX_METER and random.random() < 0.3 and dist < 450:
                self.plan = "super"
            self.plan_t = random.randint(10, 30)
        self.plan_t -= 1

        if self.plan == "walk":
            held[fwd] = True
            if dist < 90:
                self.plan_t = 0
        elif self.plan == "back":
            held[back] = True
        elif self.plan == "jump":
            held["up"] = held[fwd] = True
            self.plan = "air"
        elif self.plan == "air":
            if not me.on_ground and me.vel_y > 0 and dist < 110:
                pressed.add(random.choice(("kick", "punch")))
        elif self.plan in ("fireball", "super"):
            pressed.add("special" if self.plan == "fireball" else "super")
            self.plan = "wait"
        elif self.plan == "attack" and self.cooldown == 0:
            choice = random.choice(("punch", "punch", "kick", "sweep", "low"))
            if choice in ("sweep", "low"):
                held["down"] = True
            pressed.add("punch" if choice in ("punch", "low") else "kick")
            self.cooldown = int(random.randint(14, 34) * (1.4 - self.skill))
        return held, pressed


def separate(a, b):
    """Fighters are solid: push overlapping bodies apart (walls push the other one)."""
    if a.state in ("knockdown", "ko") or b.state in ("knockdown", "ko"):
        return
    if not a.rect.colliderect(b.rect):
        return
    overlap = BODY_W - abs(a.x - b.x)
    if overlap <= 0:
        return
    d = 1 if a.x < b.x else -1 if a.x > b.x else a.facing
    a.x -= d * overlap / 2
    b.x += d * overlap / 2
    a.clamp()
    b.clamp()
    overlap = BODY_W - abs(a.x - b.x)
    if overlap > 0:
        if a.x <= LEFT_LIMIT or a.x >= RIGHT_LIMIT:
            b.x += d * overlap
        else:
            a.x -= d * overlap
        a.clamp()
        b.clamp()


def build_stage():
    """Sunset harbour skyline, drawn once."""
    rng = random.Random(7)
    stage = pygame.Surface((WIDTH, HEIGHT))
    horizon = GROUND_Y - 30
    top, bottom = (40, 20, 70), (250, 130, 70)
    for y in range(GROUND_Y):
        k = min(1.0, y / horizon)
        pygame.draw.line(stage, tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)), (0, y), (WIDTH, y))
    pygame.draw.circle(stage, (255, 210, 130), (int(WIDTH * 0.68), GROUND_Y - 95), 52)
    for layer, (color, hmin, hmax) in enumerate((((80, 45, 90), 60, 170), ((40, 25, 55), 40, 120))):
        x = -10
        while x < WIDTH:
            w, h = rng.randint(30, 70), rng.randint(hmin, hmax)
            pygame.draw.rect(stage, color, (x, GROUND_Y - h, w, h))
            if layer == 1:
                for wy in range(GROUND_Y - h + 8, GROUND_Y - 10, 12):
                    for wx in range(x + 5, x + w - 6, 10):
                        if rng.random() < 0.3:
                            pygame.draw.rect(stage, (255, 210, 110), (wx, wy, 4, 5))
            x += w + rng.randint(0, 8)
    # crane on the quay
    pygame.draw.line(stage, (30, 20, 40), (120, GROUND_Y), (120, GROUND_Y - 190), 8)
    pygame.draw.line(stage, (30, 20, 40), (60, GROUND_Y - 180), (260, GROUND_Y - 180), 6)
    pygame.draw.line(stage, (30, 20, 40), (230, GROUND_Y - 180), (230, GROUND_Y - 120), 2)
    # floor with perspective lines
    for y in range(GROUND_Y, HEIGHT):
        k = (y - GROUND_Y) / (HEIGHT - GROUND_Y)
        pygame.draw.line(stage, shade((80, 70, 85), 1 - k * 0.45), (0, y), (WIDTH, y))
    vx, vy = WIDTH / 2, GROUND_Y - 260
    for i in range(-12, 13):
        bx = WIDTH / 2 + i * 90
        t = (GROUND_Y - vy) / (HEIGHT - vy)
        pygame.draw.line(stage, (60, 52, 66), (vx + (bx - vx) * t, GROUND_Y), (bx, HEIGHT), 2)
    for y in (GROUND_Y + 14, GROUND_Y + 34, GROUND_Y + 62):
        pygame.draw.line(stage, (60, 52, 66), (0, y), (WIDTH, y), 2)
    pygame.draw.line(stage, (200, 160, 120), (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
    return stage


def draw_health(surface, x, y, w, h, fighter, from_right, blink):
    pygame.draw.rect(surface, BLACK, (x - 3, y - 3, w + 6, h + 6))
    pygame.draw.rect(surface, (60, 20, 25), (x, y, w, h))
    trail = int(w * fighter.shown_health / MAX_HEALTH)
    cur = int(w * fighter.health / MAX_HEALTH)
    low = fighter.health <= 25 and blink
    for width, color in ((trail, RED), (cur, ORANGE if low else YELLOW)):
        bx = x + w - width if from_right else x
        pygame.draw.rect(surface, color, (bx, y, width, h))
        pygame.draw.rect(surface, shade(color, 1.25), (bx, y + 2, width, 5))


def draw_meter(surface, x, y, w, fighter, blink, font):
    pygame.draw.rect(surface, BLACK, (x - 2, y - 2, w + 4, 18))
    pygame.draw.rect(surface, (30, 30, 45), (x, y, w, 14))
    full = fighter.meter >= MAX_METER
    color = WHITE if full and blink else fighter.look["ki"]
    pygame.draw.rect(surface, color, (x, y, int(w * fighter.meter / MAX_METER), 14))
    draw_text(surface, font, "MAX" if full else "POWER", WHITE, 1, midbottom=(x + w // 2, y - 1))


def draw_interface(surface, game):
    p1, p2 = game.p1, game.p2
    blink = (game.frame // 8) % 2 == 0
    # UI Box Frame containers for Health Bars (P1 drains toward the left, P2 toward the right)
    draw_health(surface, 40, 30, 300, 25, p1, False, blink)
    draw_health(surface, WIDTH - 340, 30, 300, 25, p2, True, blink)
    draw_text(surface, game.font_small, p1.name, WHITE, topleft=(40, 62))
    draw_text(surface, game.font_small, p2.name, WHITE, topright=(WIDTH - 40, 62))
    for i in range(ROUNDS_TO_WIN):
        for f, cx in ((p1, 330 - i * 20), (p2, WIDTH - 330 + i * 20)):
            pygame.draw.circle(surface, BLACK, (cx, 72), 8)
            pygame.draw.circle(surface, YELLOW if f.wins > i else (60, 60, 70), (cx, 72), 6)
    # Round timer
    pygame.draw.rect(surface, BLACK, (WIDTH // 2 - 34, 18, 68, 50))
    pygame.draw.rect(surface, (40, 30, 60), (WIDTH // 2 - 31, 21, 62, 44))
    secs = max(0, math.ceil(game.time_left / FPS))
    draw_text(surface, game.font_mid, str(secs), RED if secs <= 10 else WHITE, center=(WIDTH // 2, 44))
    # Power gauges
    draw_meter(surface, 40, HEIGHT - 30, 220, p1, blink, game.font_tiny)
    draw_meter(surface, WIDTH - 260, HEIGHT - 30, 220, p2, blink, game.font_tiny)
    # Combo counters
    for f, (n, t) in game.combo_text.items():
        if t > 0:
            pos = dict(topleft=(40, 110)) if f is p1 else dict(topright=(WIDTH - 40, 110))
            draw_text(surface, game.font_mid, f"{n} HITS", YELLOW, **pos)
    draw_text(surface, game.font_tiny, "ESC pause  ·  F1 hitboxes", (200, 200, 210), 1,
              midbottom=(WIDTH // 2, HEIGHT - 8))


class Game:
    MENU = ("1 PLAYER  vs CPU", "2 PLAYERS", "QUIT")

    def __init__(self, screen):
        self.screen = screen
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.stage = build_stage()
        self.font_big = pygame.font.Font(None, 104)
        self.font_mid = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 30)
        self.font_tiny = pygame.font.Font(None, 22)
        self.phase = "title"
        self.menu_index = 0
        self.paused = False
        self.show_boxes = False
        self.frame = 0
        self.title_fighters = (Fighter("KAI", 190, 1, None), Fighter("ROSA", WIDTH - 190, -1, None))

    # --- match flow ---
    def new_match(self, vs_cpu):
        self.vs_cpu = vs_cpu
        self.p1 = Fighter("KAI", 200, 1, KeyboardController(P1_KEYS))
        self.p2 = Fighter("ROSA", WIDTH - 200, -1, CPUController() if vs_cpu else KeyboardController(P2_KEYS))
        self.round_no = 1
        self.start_round()

    def start_round(self):
        for f in (self.p1, self.p2):
            f.reset()
        self.projectiles = []
        self.particles = []
        self.combo_text = {}
        self.time_left = ROUND_TIME * FPS
        self.hitstop = 0
        self.shake_mag = 0
        self.super_t = 0
        self.banner = None
        self.round_winner = None
        self.paused = False
        self.set_phase("intro")

    def set_phase(self, phase):
        self.phase = phase
        self.phase_t = 0

    def announce(self, text, frames, color=WHITE):
        self.banner = [text, frames, color, 0]

    def finish_round(self):
        p1, p2 = self.p1, self.p2
        winner = p1 if p1.health > p2.health else p2 if p2.health > p1.health else None
        self.round_winner = winner
        if winner:
            winner.wins += 1
            perfect = winner.health == MAX_HEALTH
            self.announce("PERFECT!" if perfect else f"{winner.name} WINS", 150, YELLOW)
        else:
            p1.wins += 1
            p2.wins += 1
            self.announce("DRAW", 150)
        self.set_phase("roundover")

    # --- feedback ---
    def shake(self, mag):
        self.shake_mag = max(self.shake_mag, mag)

    def sparks(self, pos, colors, n):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(2, 8)
            self.particles.append([pos[0], pos[1], math.cos(a) * s, math.sin(a) * s,
                                   random.randint(12, 22), random.choice(colors)])

    def on_hit(self, attacker, defender, pos, heavy):
        self.hitstop = 14 if heavy else 6
        self.shake(8 if heavy else 3)
        self.sparks(pos, (YELLOW, WHITE, ORANGE), 22 if heavy else 12)
        if defender.combo >= 2:
            self.combo_text[attacker] = (defender.combo, 70)

    def on_block(self, pos):
        self.hitstop = 4
        self.sparks(pos, (CYAN, WHITE), 8)

    def super_freeze(self, fighter):
        self.hitstop = 26
        self.super_t = 26
        self.sparks((fighter.x, fighter.y - 70), (fighter.look["ki"], WHITE), 30)

    # --- input ---
    def on_key(self, key):
        if key == pygame.K_F1:
            self.show_boxes = not self.show_boxes
            return None
        if self.phase == "title":
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(self.MENU)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(self.MENU)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_f):
                if self.menu_index == 2:
                    return "quit"
                self.new_match(vs_cpu=self.menu_index == 0)
            elif key == pygame.K_ESCAPE:
                return "quit"
            return None
        if self.phase == "matchover":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.new_match(self.vs_cpu)
            elif key == pygame.K_ESCAPE:
                self.set_phase("title")
            return None
        if key in (pygame.K_ESCAPE, pygame.K_p):
            self.paused = not self.paused
        elif self.paused and key == pygame.K_q:
            self.paused = False
            self.set_phase("title")
        return None

    # --- simulation ---
    def step(self, keys):
        self.frame += 1
        if self.phase == "title":
            for f in self.title_fighters:
                f.anim_t += 1
            return
        if self.paused:
            return

        # effects keep moving during hitstop
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.3
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        self.shake_mag *= 0.85
        if self.super_t:
            self.super_t -= 1
        if self.banner:
            self.banner[3] += 1
            if self.banner[3] >= self.banner[1]:
                self.banner = None
        for f, (n, t) in list(self.combo_text.items()):
            self.combo_text[f] = (n, t - 1)
        if self.hitstop > 0:
            self.hitstop -= 1
            return

        p1, p2 = self.p1, self.p2
        fighting = self.phase == "fight"
        for me, opp in ((p1, p2), (p2, p1)):
            held, pressed = me.controller.read(keys, me, opp, self)
            if not fighting:
                held, pressed = NEUTRAL, set()
            me.handle_input(held, pressed, opp, self)

        slow_motion = self.phase == "ko" and self.phase_t < 90 and self.phase_t % 2
        if not slow_motion:
            p1.update(p2, self)
            p2.update(p1, self)
            separate(p1, p2)
            for p in self.projectiles:
                p.update()
            if fighting:
                self.resolve_hits()
            self.projectiles = [p for p in self.projectiles if p.alive]

        self.phase_t += 1
        if self.phase == "intro":
            if self.phase_t == 1:
                final = p1.wins == ROUNDS_TO_WIN - 1 and p2.wins == ROUNDS_TO_WIN - 1
                self.announce("FINAL ROUND" if final else f"ROUND {self.round_no}", 75)
            if self.phase_t >= 75:
                self.set_phase("fight")
                self.announce("FIGHT!", 45, YELLOW)
        elif self.phase == "fight":
            self.time_left -= 1
            if p1.health <= 0 or p2.health <= 0:
                both = p1.health <= 0 and p2.health <= 0
                self.set_phase("ko")
                self.announce("DOUBLE K.O." if both else "K.O.", 110, RED)
            elif self.time_left <= 0:
                self.time_left = 0
                self.set_phase("ko")
                self.announce("TIME", 110)
        elif self.phase == "ko":
            if self.phase_t >= 140 and p1.on_ground and p2.on_ground:
                self.finish_round()
        elif self.phase in ("roundover", "matchover"):
            w = self.round_winner
            if w and w.on_ground and w.state in ACTIONABLE:
                w.state = "win"
                w.vel_x = 0
            if self.phase == "roundover" and self.phase_t >= 160:
                if max(p1.wins, p2.wins) >= ROUNDS_TO_WIN:
                    self.set_phase("matchover")
                else:
                    self.round_no += 1
                    self.start_round()

    def resolve_hits(self):
        p1, p2 = self.p1, self.p2
        # Check both attacks first so simultaneous hits trade
        hits = []
        for att, dfn in ((p1, p2), (p2, p1)):
            box = att.attack_box()
            if box and box.colliderect(dfn.rect):
                hits.append((att, dfn, box.clip(dfn.rect).center))
        for att, dfn, pos in hits:
            att.has_hit = True
            dfn.receive_hit(MOVES[att.move], att.facing, att, self, pos)

        # Fireball vs fireball: equal ones cancel, a super eats a normal one
        for a in self.projectiles:
            for b in self.projectiles:
                if a.owner is not b.owner and a.alive and b.alive and a.rect.colliderect(b.rect):
                    if a.super != b.super:
                        (b if a.super else a).alive = False
                    else:
                        a.alive = b.alive = False
                    self.sparks(((a.x + b.x) / 2, a.y), (WHITE, a.color, b.color), 16)
        # Fireball vs fighter
        for p in self.projectiles:
            target = p2 if p.owner is p1 else p1
            if (p.alive and p.rect.colliderect(target.rect)
                    and target.state not in ("knockdown", "ko") and target.invuln == 0):
                p.alive = False
                target.receive_hit(SUPER_HIT if p.super else FIREBALL_HIT, p.dir, p.owner, self, (p.x, p.y))

    # --- rendering ---
    def draw(self):
        if self.phase == "title":
            self.draw_title()
            return
        c = self.canvas
        c.blit(self.stage, (0, 0))
        if self.super_t:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((0, 0, 20, 150))
            c.blit(veil, (0, 0))
        fighters = sorted((self.p1, self.p2), key=lambda f: f.state in ("attack", "special"))
        for f in fighters:
            f.draw_shadow(c)
        for f in fighters:
            f.draw(c)
        for p in self.projectiles:
            p.draw(c)
        for x, y, vx, vy, life, color in self.particles:
            pygame.draw.line(c, color, (x, y), (x - vx * 2, y - vy * 2), 3 if life > 8 else 2)
        if self.show_boxes:
            for f in fighters:
                pygame.draw.rect(c, GREEN, f.rect, 2)
                box = f.attack_box()
                if box:
                    pygame.draw.rect(c, YELLOW, box)   # visual attack feedback box
            for p in self.projectiles:
                pygame.draw.rect(c, YELLOW, p.rect, 2)

        m = int(self.shake_mag)
        offset = (random.randint(-m, m), random.randint(-m, m)) if m else (0, 0)
        self.screen.fill(DARK)
        self.screen.blit(c, offset)
        draw_interface(self.screen, self)

        if self.banner:
            text, frames, color, age = self.banner
            img = pygame.Surface((WIDTH, 140), pygame.SRCALPHA)
            draw_text(img, self.font_big, text, color, 4, center=(WIDTH // 2, 70))
            zoom = 1 + max(0, 8 - age) * 0.12
            if zoom != 1:
                img = pygame.transform.rotozoom(img, 0, zoom)
            self.screen.blit(img, img.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))
        if self.phase == "matchover":
            p1, p2 = self.p1, self.p2
            if p1.wins == p2.wins:
                title = "DRAW GAME"
            else:
                title = f"{(p1 if p1.wins > p2.wins else p2).name} WINS THE MATCH"
            draw_text(self.screen, self.font_mid, title, YELLOW, 3, center=(WIDTH // 2, HEIGHT // 2 - 30))
            draw_text(self.screen, self.font_small, "ENTER rematch     ESC title", WHITE,
                      center=(WIDTH // 2, HEIGHT // 2 + 20))
        if self.paused:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 160))
            self.screen.blit(veil, (0, 0))
            draw_text(self.screen, self.font_big, "PAUSED", WHITE, 4, center=(WIDTH // 2, HEIGHT // 2 - 30))
            draw_text(self.screen, self.font_small, "ESC resume     Q quit to title", WHITE,
                      center=(WIDTH // 2, HEIGHT // 2 + 30))

    def draw_title(self):
        s = self.screen
        s.blit(self.stage, (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((10, 5, 25, 120))
        s.blit(veil, (0, 0))
        for f in self.title_fighters:
            f.draw_shadow(s)
            f.draw(s)
        draw_text(s, self.font_big, "QUAY KINGS", YELLOW, 5, center=(WIDTH // 2, 80))
        draw_text(s, self.font_small, "a 2D fighting game", WHITE, center=(WIDTH // 2, 132))
        for i, item in enumerate(self.MENU):
            sel = i == self.menu_index
            label = f"> {item} <" if sel and (self.frame // 15) % 2 == 0 else item
            draw_text(s, self.font_mid if sel else self.font_small, label, YELLOW if sel else WHITE,
                      center=(WIDTH // 2, 200 + i * 44))
        lines = ("P1: A D move  W jump  S crouch  F punch  G kick  H fireball  R super",
                 "P2: Arrows  Num1/,  punch  Num2/.  kick  Num3//  fireball  Num0/RShift  super",
                 "Hold back to block  ·  land a hit, then fireball to combo  ·  ENTER to start")
        for i, line in enumerate(lines):
            draw_text(s, self.font_tiny, line, WHITE, 1, center=(WIDTH // 2, HEIGHT - 66 + i * 22))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Quay Kings")
    clock = pygame.time.Clock()
    game = Game(screen)

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and game.on_key(event.key) == "quit":
                running = False

        game.step(pygame.key.get_pressed())
        game.draw()
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
