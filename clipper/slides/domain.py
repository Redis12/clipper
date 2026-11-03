"""Vidéo « Domain War » : l'écran est une grille partagée entre 2 persos (chacun sa couleur = son domaine).
Les balles (visage du perso) traversent leur domaine et repeignent les cases adverses qu'elles touchent
(principe de Pong Wars). Chaque perso a SA fiche (`movesets.py`, library/_domain/<Perso>.txt) :
3 attaques (zone, devant, projectiles), 1 secret, 1 passif — effets communs, noms fidèles au perso.

Scénario (pour que ça raconte une histoire) :
1. échanges d'attaques normales (projectiles / devant), camps alternés ;
2. vers 42 % : celui qui PERD sort son secret → comeback ;
3. vers 64 % : l'autre sort le sien → contre-attaque (un secret « breaks: Infinity » annule ce passif adverse :
   Mahoraga s'adapte à l'Infini de Gojo, la lance de Toji le perce…) ;
4. vers 82 % : choc final, les 2 grosses attaques de zone en même temps (« DOMAIN CLASH! » si deux domaines).
On simule `tries` matchs en silence et on garde le plus serré.

Bruitages : library/_sounds/domain/ — « <Perso> <emplacement>.mp3 » (ex. « Gojo secret.mp3 », « Sukuna zone.mp3 »)
puis « <famille>.mp3 » (domain, shrine, bomb, beam, shots, timestop, teleport, summon, clones, giant, mega_beam,
regen, tick), sinon son synthétisé.
"""
from __future__ import annotations

import json
import math
import random
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .. import config, db
from ..util import log, require_bin

END_S = 1.5                                                  # écran de fin court (vidIQ : un Short « se termine », il ne traîne pas)
from . import faces, fusion, fxengine, library, movesets, render, vfxgen, vfxpack

TEAM = [(40, 120, 255), (235, 45, 70)]


def out_dir() -> Path:
    return fusion.out_dir()


def sfx_dir() -> Path:
    d = library.root() / "_sounds" / "domain"
    d.mkdir(parents=True, exist_ok=True)
    return d


def hex_rgb(h: str | None, fallback: tuple) -> tuple:
    try:
        h = (h or "").strip().lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) == 6 else fallback
    except ValueError:
        return fallback


# --------------------------------------------------------------------------- simulation

class War:
    def __init__(self, nx: int, ny: int, cell: float, seed: int, speed: float, sheets: list[dict],
                 per_team: int = 3):
        self.nx, self.ny, self.cell = nx, ny, cell
        self.Wd, self.Hd = nx * cell, ny * cell
        self.grid = [[0 if x < nx // 2 else 1 for x in range(nx)] for _ in range(ny)]
        self.flash = [[0.0] * nx for _ in range(ny)]
        self.rnd = random.Random(seed)
        self.speed = speed
        self.sheets = sheets
        self.passive = [s.get("passive", {}).get("fam", "none") for s in sheets]
        self.passive_off = [-1.0, -1.0]                      # passif annulé jusqu'à…
        self.timestop = None                                  # (équipe qui arrête le temps, fin)
        self.transformed = [None, None]                       # instant de la transformation (secret + fiche « form »)
        self.power = [1.0, 1.0]                               # bonus après transformation
        self.ki = [0.0, 0.0]                                  # jauge de Ki (0 → 100) : pleine = SPARKING + ultime
        self.sparking = [-1.0, -1.0]                          # mode Sparking jusqu'à…
        self.misses = []                                      # (t, x, y, équipe qui esquive) → « MISS! »
        self.pending = []                                     # actions programmées (t, fonction) : Vanish…
        self.beam = None                                      # Beam Clash en cours
        self.vanishes = []                                    # (t, équipe) des Vanish (son + effet)
        self.hits = []                                        # (t, équipe touchée) : son d'impact
        self.subs_left = [int(sh.get("substitute") or 0) for sh in sheets]   # permutations (jeux Naruto Storm)
        self.subs = []                                        # (t, x, y, équipe, nx, ny) : bûche à la place du perso
        self.kos = []                                         # (t, équipe, x, y) persos sortis
        self.final = False                                    # phase finale (le dernier perso peut tomber)
        self.balls = []
        for team in (0, 1):
            for j in range(per_team):
                lo = 0.1 if team == 0 else 0.6
                self.balls.append(self._ball(team, self.Wd * (lo + 0.3 * self.rnd.random()),
                                             self.Hd * (j + 0.5) / per_team, self.rnd.uniform(0, 2 * math.pi)))
        self.t = 0.0
        self.ticks = []
        self.fx = []
        self.next_regen = [2.0, 3.1]

    def _ball(self, team, x, y, a, kind="main", until=None, r=1.4):
        return {"team": team, "x": x, "y": y, "vx": math.cos(a) * self.speed, "vy": math.sin(a) * self.speed,
                "r": self.cell * r, "r0": r, "big_until": -1.0, "frozen_until": -1.0, "dies": until,
                "kind": kind, "trail": [], "hp": 3, "id": self.rnd.random(), "hurt": -9.0}

    def share(self) -> float:
        return sum(row.count(0) for row in self.grid) / (self.nx * self.ny)

    def passive_on(self, team: int, fam: str) -> bool:
        return self.passive[team] == fam and self.t >= self.passive_off[team]

    def _shields(self, team: int):
        """Centres protégés par l'Infini du camp `team` (ses balles principales)."""
        if not self.passive_on(team, "infinity"):
            return []
        return [(b["x"], b["y"]) for b in self.balls if b["team"] == team and b["kind"] == "main"]

    def paint(self, team: int, gx: int, gy: int, shields=None) -> bool:
        if not (0 <= gx < self.nx and 0 <= gy < self.ny) or self.grid[gy][gx] == team:
            return False
        cx, cy = (gx + 0.5) * self.cell, (gy + 0.5) * self.cell
        if shields:
            R2 = (self.cell * 2.8) ** 2
            if any((cx - x) ** 2 + (cy - y) ** 2 < R2 for x, y in shields):
                return False                                    # l'Infini arrête tout
        foe = 1 - team
        if self.dodging(foe):                                   # transformé : il esquive tout autour de lui
            R2 = (self.cell * 3.2) ** 2
            for b in self.mains(foe):
                if (cx - b["x"]) ** 2 + (cy - b["y"]) ** 2 < R2:
                    if not self.misses or self.t - self.misses[-1][0] > 0.45:
                        self.misses.append((self.t, b["x"], b["y"], foe))
                    return False
        self.grid[gy][gx] = team
        self.flash[gy][gx] = 1.0
        self.ki[team] = min(100.0, self.ki[team] + 0.2)
        return True

    def dodging(self, team: int) -> bool:
        """Juste après une transformation (6 s) : esquive les attaques (« MISS! »)."""
        tt = self.transformed[team]
        return tt is not None and tt <= self.t < tt + 6.0

    def vanish(self, team: int) -> None:
        """Disparaît et réapparaît derrière un ennemi, le fige et repeint autour (Ultra Instinct…)."""
        mine, enemies = self.mains(team), self.mains(1 - team)
        if not mine or not enemies:
            return
        b = self.rnd.choice(mine)
        e = self.rnd.choice(enemies)
        ang = math.atan2(e["vy"], e["vx"]) + math.pi
        fx = {"slot": "fx", "fam": "vanish", "team": team, "t0": self.t, "x0": b["x"], "y0": b["y"], "dur": 0.5,
              "ball": b, "name": ""}
        b["x"] = min(max(e["x"] + math.cos(ang) * self.cell * 2.6, b["r"]), self.Wd - b["r"])
        b["y"] = min(max(e["y"] + math.sin(ang) * self.cell * 2.6, b["r"]), self.Hd - b["r"])
        e["frozen_until"] = max(e["frozen_until"], self.t + 1.3)
        fx.update(x=b["x"], y=b["y"], radius=self.cell * 4.2, delay=0.05)
        self.fx.append(fx)
        self.vanishes.append((self.t, team))

    def damage(self, b: dict, fx: dict | None = None) -> None:
        """Une grosse attaque touche un perso : −1 PV (une fois par attaque) ; 3 coups = K.O. Les deux camps
        sont égaux : plus de persos « intouchables ». Avant la phase finale, on ne sort jamais le dernier."""
        if b["kind"] != "main" or b.get("dies") is not None or self.dodging(b["team"]):
            return
        if self.subs_left[b["team"]] > 0 and not self.final and fx is not None and self.rnd.random() < 0.55:
            hit = fx.setdefault("hit", set())                   # PERMUTATION : une bûche prend le coup,
            if b["id"] in hit:                                  # le perso réapparaît plus loin
                return
            hit.add(b["id"])
            self.subs_left[b["team"]] -= 1
            x0, y0 = b["x"], b["y"]
            ang = self.rnd.uniform(0, 2 * math.pi)
            b["x"] = min(max(x0 + math.cos(ang) * self.cell * 5, b["r"]), self.Wd - b["r"])
            b["y"] = min(max(y0 + math.sin(ang) * self.cell * 5, b["r"]), self.Hd - b["r"])
            self.subs.append((self.t, x0, y0, b["team"], b["x"], b["y"]))
            return
        key = id(fx) if fx is not None else None
        if fx is not None:
            hit = fx.setdefault("hit", set())
            if b["id"] in hit:
                return
            hit.add(b["id"])
        b["hp"] -= 1
        b["hurt"] = self.t
        self.hits.append((self.t, b["team"]))
        b["frozen_until"] = max(b["frozen_until"], self.t + 0.8)
        if b["hp"] <= 0:
            if not self.final and len(self.mains(b["team"])) <= 1:
                b["hp"] = 1
                return
            b["dies"] = self.t
            self.kos.append((self.t, b["team"], b["x"], b["y"]))
        _ = key

    def hit_disc(self, team, x, y, R, fx) -> None:
        for e in self.balls:
            if e["team"] != team and (e["x"] - x) ** 2 + (e["y"] - y) ** 2 < (R + e["r"] * 0.5) ** 2:
                self.damage(e, fx)

    def start_beam_clash(self, winner: int) -> None:
        """Les 2 rayons se rencontrent au milieu ; la jauge oscille puis `winner` pousse tout."""
        self.beam = {"t0": self.t, "dur": 3.6, "winner": winner, "pos": 0.5, "y": self.Hd / 2, "half": 2}
        for b in self.balls:
            b["frozen_until"] = max(b["frozen_until"], self.t + 3.6)

    def paint_disc(self, team, x, y, R) -> bool:
        sh = self._shields(1 - team)
        c = self.cell
        n = int(R / c) + 1
        got = False
        gx0, gy0 = int(x / c), int(y / c)
        for gy in range(gy0 - n, gy0 + n + 1):
            for gx in range(gx0 - n, gx0 + n + 1):
                if ((gx + 0.5) * c - x) ** 2 + ((gy + 0.5) * c - y) ** 2 <= R * R:
                    got |= self.paint(team, gx, gy, sh)
        return got

    def paint_band(self, team, x, y, ang, length, half) -> bool:
        sh = self._shields(1 - team)
        c = self.cell
        dx, dy = math.cos(ang), math.sin(ang)
        got = False
        for i in range(int(length / (c * 0.5))):
            px, py = x + dx * i * c * 0.5, y + dy * i * c * 0.5
            for o in range(-int(half), int(half) + 1):
                got |= self.paint(team, int((px - dy * o * c) / c), int((py + dx * o * c) / c), sh)
        return got

    def mains(self, team):
        return [b for b in self.balls if b["team"] == team and b["kind"] == "main" and b.get("dies") is None]

    def enemy_target(self, team):
        """Une case adverse plutôt au cœur du camp adverse."""
        cells = [(gx, gy) for gy in range(self.ny) for gx in range(self.nx) if self.grid[gy][gx] != team]
        if not cells:
            return self.Wd / 2, self.Hd / 2
        mx = sum(c[0] for c in cells) / len(cells)
        my = sum(c[1] for c in cells) / len(cells)
        cells.sort(key=lambda c: (c[0] - mx) ** 2 + (c[1] - my) ** 2)
        gx, gy = self.rnd.choice(cells[: max(1, len(cells) // 4)])
        return (gx + 0.5) * self.cell, (gy + 0.5) * self.cell

    # --- attaques
    def launch(self, team: int, slot: str) -> dict:
        mv = self.sheets[team].get(slot) or {"name": slot, "fam": movesets.DEFAULT_SLOTS[slot]}
        fam = mv["fam"]
        pool = self.mains(team) or [x for x in self.balls if x["team"] == team]
        if not pool:                                            # plus personne : rien ne part
            return {"slot": slot, "fam": "none", "team": team, "t0": self.t, "x": 0, "y": 0, "name": mv["name"],
                    "dur": 0.0, "ball": None}
        b = self.rnd.choice(pool)
        fx = {"slot": slot, "fam": fam, "team": team, "t0": self.t, "x": b["x"], "y": b["y"], "name": mv["name"],
              "dur": 0.45, "ball": b}
        c = self.cell
        if slot == "secret" and self.sheets[team].get("form") and self.transformed[team] is None:
            self.transformed[team] = self.t                   # transformation : plus gros, plus vite, plus fort
            self.power[team] = 1.45
            for x in self.mains(team):
                x["r0"] = 1.75
            fx["transform"] = True
        pw = self.power[team]
        if fam in ("bomb", "meteor"):
            tx, ty = self.enemy_target(team)
            big = fam == "meteor"
            fx.update(fam="bomb", sound=fam, tx=tx, ty=ty, radius=c * (11 if big else 6) * pw, dur=1.0,
                      delay=0.8 if big else 0.5)
        elif fam in ("domain", "shrine"):
            fx.update(radius=c * (7.5 if fam == "domain" else 8.5) * pw, dur=1.0)
            if fam == "domain":
                fx["freeze"] = True
        elif fam == "beam":
            ang = (0 if team == 0 else math.pi) + self.rnd.uniform(-0.5, 0.5)
            fx.update(ang=ang, length=math.hypot(self.Wd, self.Hd), half=1)
        elif fam == "mega_beam":
            fx.update(ang=0 if team == 0 else math.pi, x=0 if team == 0 else self.Wd, length=self.Wd, half=4,
                      dur=0.7)
        elif fam == "shots":
            fx["shots"] = [self.enemy_target(team) for _ in range(7 if pw > 1 else 5)]
            fx["dur"] = 0.6
        elif fam == "timestop":
            self.timestop = (team, self.t + 3.0)
            for e in self.balls:
                if e["team"] != team:
                    e["frozen_until"] = self.t + 3.0
            fx["dur"] = 3.0
        elif fam == "teleport":                              # 3 Vanish d'affilée
            for k in range(4):
                self.pending.append((self.t + 0.15 + k * 0.5, lambda tm=team: self.vanish(tm)))
            fx["dur"] = 0.3
        elif fam == "summon":
            s = self._ball(team, b["x"], b["y"], self.rnd.uniform(0, 2 * math.pi), "summon", self.t + 5.0, 2.1)
            self.balls.append(s)
            fx.update(dur=0.3, summon=mv.get("summon") or mv["name"])
        elif fam == "clones":
            for _ in range(4):
                self.balls.append(self._ball(team, b["x"], b["y"], self.rnd.uniform(0, 2 * math.pi), "clone",
                                             self.t + 5.0, 1.0))
            fx["dur"] = 0.3
        elif fam == "giant":
            b["big_until"] = self.t + 2.2
            fx["dur"] = 2.2
        if mv.get("breaks"):                                    # ce secret annule un passif adverse
            if movesets.parse(f"passive: {mv['breaks']}")["passive"]["fam"] == self.passive[1 - team] or \
                    mv["breaks"] in (self.sheets[1 - team].get("passive", {}).get("name", "").lower(),):
                self.passive_off[1 - team] = self.t + 6.0
                fx["broke"] = self.sheets[1 - team]["passive"]["name"]
        self.fx.append(fx)
        return fx

    def _apply(self, fx) -> None:
        age = self.t - fx["t0"] - fx.get("delay", 0)
        if age < 0:
            return
        a = min(1.0, age / max(0.01, fx["dur"] if fx["fam"] not in ("timestop", "giant") else 0.4))
        team, fam, got = fx["team"], fx["fam"], False
        big = fx.get("slot") in ("zone", "secret", "fx")
        if fam == "bomb":
            R = fx["radius"] * min(1, age / 0.4)
            got = self.paint_disc(team, fx["tx"], fx["ty"], R)
            if big and age >= 0.3:
                self.hit_disc(team, fx["tx"], fx["ty"], R, fx)
        elif fam in ("domain", "shrine"):
            b = fx["ball"]
            R = fx["radius"] * a
            got = self.paint_disc(team, b["x"], b["y"], R)
            if a >= 0.6:
                self.hit_disc(team, b["x"], b["y"], R, fx)
            if fx.get("freeze"):
                for e in self.balls:
                    if e["team"] != team and (e["x"] - b["x"]) ** 2 + (e["y"] - b["y"]) ** 2 < R * R:
                        e["frozen_until"] = max(e["frozen_until"], self.t + 2.0)
        elif fam in ("beam", "mega_beam"):
            L = fx["length"] * a
            got = self.paint_band(team, fx["x"], fx["y"], fx["ang"], L, fx["half"])
            if fam == "mega_beam" or big:                       # le rayon touche les persos sur son passage
                dx, dy = math.cos(fx["ang"]), math.sin(fx["ang"])
                for e in self.balls:
                    if e["team"] == team:
                        continue
                    rx, ry = e["x"] - fx["x"], e["y"] - fx["y"]
                    along = rx * dx + ry * dy
                    if 0 <= along <= L and abs(-rx * dy + ry * dx) < self.cell * (fx["half"] + 1) + e["r"]:
                        self.damage(e, fx)
        elif fam == "shots":
            for i, (tx, ty) in enumerate(fx["shots"]):
                if age >= 0.3 + i * 0.05:
                    got |= self.paint_disc(team, tx, ty, self.cell * 1.8)
        elif fam == "vanish":
            got = self.paint_disc(team, fx["x"], fx["y"], fx["radius"] * min(1, age / 0.25))
            self.hit_disc(team, fx["x"], fx["y"], self.cell * 3.0, fx)
        if got:
            self.ticks.append((self.t, team))

    def step(self, dt: float) -> None:
        Wd, Hd = self.Wd, self.Hd
        self.balls = [b for b in self.balls if b["dies"] is None or b["dies"] > self.t]
        if self.timestop and self.t > self.timestop[1]:
            self.timestop = None
        shields = [self._shields(0), self._shields(1)]
        self.parity = 1 - getattr(self, "parity", 0)           # ordre alterné : aucun camp n'a « le dernier mot »
        for b in (self.balls if self.parity else list(reversed(self.balls))):
            if self.t < b["frozen_until"]:
                continue
            big = self.t < b["big_until"]
            k = (1.3 if self.passive_on(b["team"], "speed") else 1.0) * (1.5 if self.power[b["team"]] > 1 else 1.0)
            if self.t < self.sparking[b["team"]]:
                k *= 1.25
            if self.timestop and self.timestop[0] == b["team"]:
                k *= 1.5
            b["r"] = self.cell * (3.8 if big else b["r0"])
            sh = shields[1 - b["team"]]
            for axis in ("x", "y"):
                v = "v" + axis
                lim = Wd if axis == "x" else Hd
                nx = b[axis] + b[v] * dt * k
                if nx - b["r"] < 0 or nx + b["r"] > lim:
                    b[v] = -b[v]
                    nx = min(max(nx, b["r"]), lim - b["r"])
                pos = (nx, b["y"]) if axis == "x" else (b["x"], nx)
                hit = self._hits(b, *pos)
                if hit:
                    got = False
                    for gx, gy in hit:
                        got |= self.paint(b["team"], gx, gy, sh)
                    if got:
                        self.ticks.append((self.t, b["team"]))
                    if big:
                        b[axis] = nx
                    else:
                        b[v] = -b[v]
                else:
                    b[axis] = nx
            sp = math.hypot(b["vx"], b["vy"])
            a = math.atan2(b["vy"], b["vx"]) + self.rnd.uniform(-0.03, 0.03)
            b["vx"], b["vy"] = math.cos(a) * sp, math.sin(a) * sp
            if big or k > 1.3:
                b["trail"] = (b["trail"] + [(b["x"], b["y"])])[-8:]
            elif b["trail"]:
                b["trail"] = b["trail"][1:]
        for team in (0, 1):                                      # passif « regen » : repeint autour de lui
            if self.passive_on(team, "regen") and self.t >= self.next_regen[team] and self.mains(team):
                b = self.rnd.choice(self.mains(team))
                if self.paint_disc(team, b["x"], b["y"], self.cell * 1.6):
                    self.ticks.append((self.t, team))
                self.fx.append({"slot": "passive", "fam": "regen", "team": team, "t0": self.t, "x": b["x"],
                                "y": b["y"], "dur": 0.5, "ball": b, "name": ""})
                self.next_regen[team] = self.t + 3.2
        due = [a for a in self.pending if a[0] <= self.t]
        if due:
            self.pending = [a for a in self.pending if a[0] > self.t]
            for _, fn in due:
                fn()
        if self.beam:                                           # Beam Clash : chaque rayon repeint son côté
            bc = self.beam
            a = min(1.0, (self.t - bc["t0"]) / bc["dur"])
            w = bc["winner"]
            push = (a - 0.72) / 0.28 if a > 0.72 and w >= 0 else 0.0   # à la fin, le gagnant pousse tout
            wobble = 0.16 * math.sin((self.t - bc["t0"]) * 7.3) * (1 - push) + 0.06 * math.sin((self.t - bc["t0"]) * 17)
            bias = 0.0 if w < 0 else (0.07 * a if a <= 0.72 else 0.07 + 0.43 * push ** 1.5) * (1 if w == 0 else -1)
            bc["pos"] = min(1.0, max(0.0, 0.5 + wobble * (1 - push) + bias))
            xm = bc["pos"] * self.Wd
            if self.parity:
                got0 = self.paint_band(0, 0, bc["y"], 0.0, xm, bc["half"])
                got1 = self.paint_band(1, self.Wd, bc["y"], math.pi, self.Wd - xm, bc["half"])
            else:
                got1 = self.paint_band(1, self.Wd, bc["y"], math.pi, self.Wd - xm, bc["half"])
                got0 = self.paint_band(0, 0, bc["y"], 0.0, xm, bc["half"])
            if got0:
                self.ticks.append((self.t, 0))
            if got1:
                self.ticks.append((self.t, 1))
            if a >= 1.0:                                        # explosion au bout
                if w < 0:                                       # égalité : explosion au milieu, les 2 encaissent
                    ex = bc["pos"] * self.Wd
                    for e in self.mains(0) + self.mains(1):
                        self.damage(e, bc)
                    w = 0
                else:
                    ex = self.Wd if w == 0 else 0.0
                    self.paint_disc(w, ex, bc["y"], self.cell * 7)
                    for e in self.mains(1 - w):                  # le perdant du clash encaisse
                        self.damage(e, bc)
                self.fx.append({"slot": "fx", "fam": "bomb", "team": w, "t0": self.t, "tx": ex, "ty": bc["y"],
                                "radius": self.cell * 7, "dur": 1.0, "delay": 0.0, "x": ex, "y": bc["y"],
                                "name": "", "ball": None})
                self.beam = None
        for team in (0, 1):
            self.ki[team] = min(100.0, self.ki[team] + dt * 1.2)
        for fx in self.fx:
            if self.t - fx["t0"] <= fx.get("delay", 0) + fx["dur"] + 0.05:
                self._apply(fx)
        self.fx = [f for f in self.fx if self.t - f["t0"] < f.get("delay", 0) + max(1.2, f["dur"] + 0.3)]
        for row in self.flash:
            for i, f in enumerate(row):
                if f:
                    row[i] = max(0.0, f - dt * 3)
        self.t += dt

    def _hits(self, b, x, y):
        r, c = b["r"], self.cell
        out = []
        for gy in range(max(0, int((y - r) / c)), min(self.ny, int((y + r) / c) + 1)):
            for gx in range(max(0, int((x - r) / c)), min(self.nx, int((x + r) / c) + 1)):
                if self.grid[gy][gx] == b["team"]:
                    continue
                px = min(max(x, gx * c), (gx + 1) * c)
                py = min(max(y, gy * c), (gy + 1) * c)
                if (px - x) ** 2 + (py - y) ** 2 < r * r:
                    out.append((gx, gy))
        return out


class Director:
    """Le scénario : attaques normales alternées (jauge de Ki pleine → SPARKING + ultime), le perso EN DANGER
    sort son secret / se transforme (< 40 % de l'écran), l'autre répond, choc final (Domain Clash ou Beam Clash),
    puis le perdant s'effondre jusqu'à la dernière case."""

    def __init__(self, war: War, seconds: float, rnd: random.Random, winner: int | None = None):
        self.war, self.S, self.rnd = war, seconds, rnd
        self.draw = winner == -1                                  # scénario « égalité » (Vallée de la Fin)
        self.winner = None if self.draw else winner               # scénario imposé : ce camp gagne (None = hasard)
        self.s1_open, self.s1_late = seconds * 0.30, seconds * 0.56
        self.s1 = self.s2 = None
        self.clash = seconds * 0.82
        self.done = set()
        self.next_t, self.team = rnd.uniform(1.8, 2.6), rnd.randrange(2)
        self.cycle = [0, 0]
        self.first_secret = None
        self.secret_share = None                                  # sa part de l'écran au moment du secret
        self.events = []                                          # (temps, équipe, emplacement, fx)
        self.combos = []                                          # attaques enchaînées après un secret (fiche « combo: »)
        self.kos = war.kos
        self.sparks = []                                          # (temps, équipe) des SPARKING
        fams = {(war.sheets[i].get("zone") or {}).get("fam") for i in (0, 1)}
        self.domain_clash = fams <= {"domain", "shrine"}
        self.final_from = self.clash + (2.5 if self.domain_clash else 4.4)
        self.leader, self.next_ko = None, 0.0
        self.ult_at = [None, None]
        self.wipe_at = self.wipe_last = None
        self.finish = None                                        # (t, x, y, équipe) : le dernier perso tombe
        self.split_at = 1e9

    def _split(self, t) -> None:
        """Égalité : le terrain se partage pile en deux (gauche / droite) en 0,9 s, depuis le centre."""
        war = self.war
        if t < self.split_at:
            return
        mid = war.nx / 2
        wrong = [(gx, gy) for gy in range(war.ny) for gx in range(war.nx)
                 if war.grid[gy][gx] != (0 if gx < mid else 1)]
        if not wrong:
            if t >= self.split_at + 1.3:
                war.draw_done = True
            return
        left = max(0.05, self.split_at + 0.9 - t)
        n = max(1, math.ceil(len(wrong) * min(1.0, (1 / 30) / left)))
        wrong.sort(key=lambda c: (abs(c[0] + 0.5 - mid), abs(c[1] - war.ny / 2)))
        for gx, gy in wrong[:n]:
            war.grid[gy][gx] = 0 if gx < mid else 1
            war.flash[gy][gx] = 1.0
        war.ticks.append((t, 0))

    def _wipe(self, t, lead, lose) -> None:
        """Plus aucun perso en face : 1 s après, une vague part du gagnant et prend tout en ~2,5 s
        (avant : 15–20 s de « grignotage » où les gens décrochent)."""
        war = self.war
        if self.wipe_at is None:                                  # juste après le FINISH : tout bascule vite
            self.wipe_at, self.wipe_last = t + 0.05, t + 0.05
            return
        if t < self.wipe_at:
            return
        cells = [(gx, gy) for gy in range(war.ny) for gx in range(war.nx) if war.grid[gy][gx] == lose]
        if not cells:
            return
        mine = war.mains(lead)
        if self.finish is not None:                               # la vague part du perso qui vient de tomber
            cx, cy = self.finish[1] / war.cell, self.finish[2] / war.cell
        else:
            cx = mine[0]["x"] / war.cell if mine else war.nx / 2
            cy = mine[0]["y"] / war.cell if mine else war.ny / 2
        left = max(0.05, self.wipe_at + 0.9 - t)
        n = max(1, math.ceil(len(cells) * min(1.0, (t - self.wipe_last) / left)))
        self.wipe_last = t
        cells.sort(key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)
        for gx, gy in cells[:n]:
            war.grid[gy][gx] = lead
            war.flash[gy][gx] = 1.0
        war.ticks.append((t, lead))

    def _fire(self, team, slot):
        fx = self.war.launch(team, slot)
        self.events.append((self.war.t, team, slot, fx))
        combo = str(self.war.sheets[team].get("combo") or "").strip().lower()
        if slot == "secret" and combo in ("zone", "front", "shots"):   # fiche « combo: zone » : le secret
            self.combos.append((self.war.t + 0.5, team, combo))         # enchaîne direct (Susanoo → Kirin)
        return fx

    def busy(self, t) -> bool:
        return any(x is not None and abs(t - x) < 1.4 for x in (self.s1, self.s2, self.clash))

    def tick(self) -> None:
        t, war = self.war.t, self.war
        for cb in [c_ for c_ in getattr(self, "combos", []) if t >= c_[0]]:
            self.combos.remove(cb)
            self._fire(cb[1], cb[2])
        s = war.share()
        if "s1" not in self.done and t >= self.s1_open:           # le perso en danger se transforme
            behind = 0 if s < 0.5 else 1
            mine = s if behind == 0 else 1 - s
            if mine <= 0.40 or t >= self.s1_late:
                self.s1, self.first_secret, self.secret_share = t, behind, mine
                self._fire(behind, "secret")
                self.done.add("s1")
                self.s2 = t + max(4.0, self.S * 0.2)
                self.next_t = t + 2.4
        if "s2" not in self.done and self.s2 is not None and t >= self.s2:
            self._fire(1 - self.first_secret, "secret")
            self.done.add("s2")
            self.next_t = t + 2.4
        if "clash" not in self.done and t >= self.clash:
            if self.domain_clash:
                first = self.rnd.randrange(2)                     # ordre tiré au sort (pas d'avantage de côté)
                for team in (first, 1 - first):
                    self._fire(team, "zone")
            else:                                                 # Beam Clash : les 2 rayons se rencontrent
                w = self.winner
                if self.draw:
                    w = -1                                        # égalité : la jauge reste au milieu
                elif w is None:
                    w = 0 if s < 0.5 else 1                       # le mené gagne le clash (retournement)
                    if self.rnd.random() < 0.35:
                        w = 1 - w
                war.start_beam_clash(w)
                for team in (0, 1):
                    fx = {"slot": "front", "fam": "beam_clash", "team": team, "t0": t, "dur": 3.6,
                          "name": (war.sheets[team].get("front") or {}).get("name", "Beam"), "x": 0, "y": 0}
                    self.events.append((t, team, "clash", fx))
            self.done.add("clash")
            self.next_t = self.final_from
        if self.draw and t >= self.clash + (2.5 if self.domain_clash else 3.95):     # égalité : après le choc
            war.final = True
            if self.finish is None:                               # double K.O. au même instant
                for team in (0, 1):
                    for b in war.mains(team):
                        b["dies"] = t
                        self.kos.append((t, team, b["x"], b["y"]))
                self.finish = (t, war.Wd / 2, war.Hd / 2, -1)
                self.split_at = t + 0.05
            self._split(t)
            return
        if t >= self.final_from:                                  # phase finale : jusqu'à la dernière case
            war.final = True
            if self.leader is None:
                self.leader = 0 if s >= 0.5 else 1
                if self.winner is not None:
                    self.leader = self.winner
                self.next_ko = t + 2.0
            lead, lose = self.leader, 1 - self.leader
            war.passive_off[lose] = t + 99
            alive = war.mains(lose)
            loser_share = 1 - s if lead == 0 else s
            if alive and (t >= self.next_ko or loser_share < (0.1, 0.22, 0.35)[len(alive) - 1]):
                b = alive.pop(0)
                b["dies"] = t
                self.kos.append((t, lose, b["x"], b["y"]))
                self.next_ko = t + 2.5
            if not alive:
                if self.finish is None:                           # le dernier perso vient de tomber → FINISH!
                    last = [k_ for k_ in self.kos if k_[1] == lose]
                    fx_, fy_ = (last[-1][2], last[-1][3]) if last else (war.Wd / 2, war.Hd / 2)
                    self.finish = (t, fx_, fy_, lose)
                for b in war.balls:
                    if b["team"] == lose:
                        b["dies"] = t
                self._wipe(t, lead, lose)
            if t >= self.next_t and war.mains(lead):
                slot = ("shots", "front", "zone")[self.cycle[lead] % 3]
                self.cycle[lead] += 1
                self._fire(lead, slot)
                self.next_t = t + (1.0 if not alive else 1.5)
            return
        for team in (0, 1):                                       # jauge de Ki pleine → SPARKING puis ultime
            if self.ult_at[team] is not None and t >= self.ult_at[team]:
                self.ult_at[team] = None
                self._fire(team, "zone")
            elif (war.ki[team] >= 100 and not self.busy(t) and t < self.clash - 3 and self.ult_at[team] is None
                  and sum(1 for _, tm in self.sparks if tm == team) < 2                       # 2 max par perso
                  and all(t - t0 > 6.0 for t0, _ in self.sparks)):                         # pas en rafale
                war.ki[team] = 0.0
                war.sparking[team] = t + 3.0
                self.sparks.append((t, team))
                self.ult_at[team] = t + 0.9
        if t >= self.next_t and not self.busy(t):
            slot = ("shots", "front")[self.cycle[self.team] % 2]
            self.cycle[self.team] += 1
            self._fire(self.team, slot)
            self.team = 1 - self.team
            self.next_t = t + self.rnd.uniform(2.4, 3.2)


GEOM = {"top": 0.135, "bottom": 0.78, "margin": 0.04}


def geometry(W: int, H: int, cells_x: int = 26):
    gw = W * (1 - 2 * GEOM["margin"])
    cell = gw / cells_x
    ny = int(H * (GEOM["bottom"] - GEOM["top"]) / cell)
    return cells_x, ny, cell, W * GEOM["margin"], H * GEOM["top"]


def make(seed: int, seconds: float, W: int, H: int, sheets: list[dict], winner: int | None = None):
    nx, ny, cell, _, _ = geometry(W, H)
    war = War(nx, ny, cell, seed, nx * cell * 0.55, sheets)
    return war, Director(war, seconds, random.Random(seed + 1), winner)


def simulate(seed: int, seconds: float, W: int, H: int, sheets: list[dict], fps: int = 30,
             winner: int | None = None) -> dict:
    war, dr = make(seed, seconds, W, H, sheets, winner)
    lead, changes, at_s1, after, final_close, clash_share = 0, 0, None, None, None, 0.5
    while not finished(war, seconds):
        dr.tick()
        for _ in range(4):
            war.step(1 / fps / 4)
        s = war.share()
        now = 1 if s > 0.51 else (-1 if s < 0.49 else 0)
        if now and now != lead:
            changes += lead != 0
            lead = now
        if at_s1 is None and dr.s1 is not None:
            at_s1 = s
        if after is None and dr.s2 is not None and war.t >= dr.s2:
            after = s
        if final_close is None and war.t >= dr.clash + 2.4:
            final_close = abs(s - 0.5)
            clash_share = s
    s = war.share()
    end = war.t
    comeback = at_s1 is not None and after is not None and (at_s1 - 0.5) * (after - 0.5) < 0
    return {"seed": seed, "changes": changes, "share": max(s, 1 - s), "comeback": comeback,
            "end": end, "close": final_close, "winner": 0 if s >= 0.5 else 1, "first_secret": dr.first_secret, "secret_share": dr.secret_share,
            "at_clash": clash_share}


def finished(war: War, seconds: float) -> bool:
    """Fini quand un camp a TOUT l'écran (filet : au-delà de seconds + 35 s, le leader prend le reste)."""
    if getattr(war, "draw_done", False):                       # égalité : terrain coupé en deux
        return True
    s = war.share()
    if s in (0.0, 1.0):
        return True
    if war.t > seconds + 35:
        lead = 0 if s >= 0.5 else 1
        for row in war.grid:
            row[:] = [lead] * len(row)
        return True
    return False


def pick_seed(seconds, W, H, sheets, tries: int = 10, rnd: random.Random | None = None,
              winner: int | None = None, comeback: bool = False, underdog: int | None = None) -> int:
    """Le match le plus prenant. Avec un scénario (gagnant imposé, comeback = il perd d'abord, sort son secret
    en premier puis gagne) : on cherche jusqu'à 4× plus de matchs qui le suivent naturellement."""
    rnd = rnd or random.Random()
    best, score = None, -1e9
    n = tries * (4 if winner is not None else 1)
    for i in range(n):
        r = simulate(rnd.randrange(1_000_000), seconds, W, H, sheets, winner=winner)
        sc = r["changes"] * 1.5 + (4 if r["comeback"] else 0) - (r["close"] or 0.5) * 30 \
            - max(0, r["end"] - seconds - 18) * 0.5
        if winner == -1:                                                 # égalité : choc final serré,
            sc += 40 - abs(r["at_clash"] - 0.5) * 120                    # l'outsider perd d'abord puis revient
            if comeback and underdog is not None:
                sc += 30 if r["first_secret"] == underdog else 0
                sc += 15 if (r["secret_share"] or 1) <= 0.40 else 0
        elif winner is not None:
            mine = r["at_clash"] if winner == 0 else 1 - r["at_clash"]     # sa part au choc final
            sc += 40 if r["winner"] == winner else 0
            sc -= max(0.0, 0.45 - mine) * 60                             # pas de victoire « sortie de nulle part »
            if comeback:
                sc += 30 if r["first_secret"] == winner else 0           # il était derrière → secret en premier
                sc += 15 if (r["secret_share"] or 1) <= 0.40 else 0      # et vraiment en danger
        if sc > score:
            best, score = r, sc
        if winner is not None and i >= tries and score > 60:
            break
    return best["seed"]


# --------------------------------------------------------------------------- son

def _synth(fam: str):
    import numpy as np
    R = fusion.RATE
    rng = np.random.default_rng(7)

    def t_(sec):
        return np.arange(int(sec * R)) / R
    if fam == "tick":
        t = t_(0.05)
        x = np.sin(2 * np.pi * 1100 * t) * np.exp(-t * 70)
    elif fam in ("domain", "giant"):
        t = t_(1.8)
        x = np.sin(2 * np.pi * (55 + 35 * np.exp(-t * 4)) * t) * np.exp(-t * 1.6) + rng.normal(0, .3, len(t)) * np.exp(-t * 5)
        x = fusion._lowpass(x.astype(np.float32), 400)
    elif fam in ("beam", "mega_beam"):
        L = 1.0 if fam == "beam" else 1.6
        t = t_(L)
        f = 200 + 1800 * np.clip(t / 0.35, 0, 1) ** 2
        x = np.sin(2 * np.pi * np.cumsum(f) / R) * np.where(t < .35, t / .35, np.exp(-(t - .35) * (5 if L < 1.5 else 2)))
        x = x + rng.normal(0, .25, len(t)) * np.where(t > .35, np.exp(-(t - .35) * 4), 0)
    elif fam in ("bomb", "meteor"):
        t = t_(1.0)
        x = rng.normal(0, 1, len(t)) * np.exp(-t * 18) + np.sin(2 * np.pi * 60 * t) * np.exp(-t * 4) * 1.4
    elif fam in ("shrine", "slash"):
        n = int(1.2 * R)
        x = np.zeros(n)
        for k in range(8):
            i, m = int(k * 0.12 * R), int(0.08 * R)
            seg = rng.normal(0, 1, m) * np.exp(-np.arange(m) / R * 40)
            x[i:i + m] += seg - np.convolve(seg, np.ones(12) / 12, "same")
    elif fam == "shots":
        n = int(0.6 * R)
        x = np.zeros(n)
        for k in range(5):
            i = int((0.3 + k * 0.05) * R)
            m = int(0.07 * R)
            tt = np.arange(m) / R
            x[i:i + m] += np.sin(2 * np.pi * 180 * tt) * np.exp(-tt * 50) + rng.normal(0, .4, m) * np.exp(-tt * 60)
    elif fam == "timestop":                                     # « ZA WARUDO » : son qui descend + tic-tac
        t = t_(2.2)
        x = np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 2.5) + 60) / R) * np.exp(-t * 0.9) * 0.8
        for k in range(4):
            i = int((0.9 + k * 0.33) * R)
            m = int(0.03 * R)
            x[i:i + m] += np.sin(2 * np.pi * 2400 * np.arange(m) / R) * 0.6
    elif fam == "teleport":
        t = t_(0.35)
        x = np.sin(2 * np.pi * np.cumsum(3000 * np.exp(-t * 12) + 300) / R) * np.exp(-t * 6)
    elif fam == "summon":                                       # cor grave
        t = t_(2.0)
        x = sum(np.sin(2 * np.pi * f * t) / (j + 1) for j, f in enumerate((73, 110, 146))) * np.minimum(1, t / .3) * np.exp(-t * 1.2)
    elif fam == "clones":
        n = int(0.7 * R)
        x = np.zeros(n)
        for k in range(4):
            i, m = int(k * 0.12 * R), int(0.12 * R)
            x[i:i + m] += fusion._lowpass(rng.normal(0, 1, m).astype(np.float32), 900) * np.exp(-np.arange(m) / R * 30)
    elif fam == "regen":
        t = t_(0.4)
        x = (np.sin(2 * np.pi * 880 * t) + np.sin(2 * np.pi * 1320 * t)) * np.exp(-t * 9) * 0.4
    else:
        t = t_(0.8)
        x = fusion._lowpass(rng.normal(0, 1, len(t)).astype(np.float32), 1500) * np.sin(np.pi * t / 0.8) ** 2
    x = np.asarray(x, dtype=np.float32)
    return x / (float(np.max(np.abs(x))) or 1)


def sfx(fam: str, fighter: str | None = None, slot: str | None = None, move: str | None = None,
        mode: str = "auto", seed: int = 0, franchise: str | None = None):
    """Bruitage dans library/_sounds/domain/ : « <Attaque> » (ex. « Kamehameha.mp3 »), puis « <Perso> <emplacement> »
    (« Gojo secret.mp3 »), puis « <famille> », sinon sons CC0 retravaillés / synthétisés."""
    d = sfx_dir()
    names = [move] if move else []
    if fighter and slot:
        first = fighter.split()[0] if fighter.split() else fighter
        names += [f"{fighter} {slot}", f"{first} {slot}"] + [f"{w} {slot}" for w in fighter.split()[1:]]
    names.append(fam)
    for n in names:
        for p in d.glob("*"):
            if p.stem.lower() == n.lower() and p.suffix.lower() in fusion.SOUND_EXT:
                return fusion.load_sound(p)
    if mode != "off":                      # banque library/_sfx/ (packs de l'utilisateur, découpés en prises)
        try:
            from . import sfxbank
            x = sfxbank.sound(fam, mode, seed, move, franchise)
            if x is not None:
                return x
        except Exception as e:
            log.info("banque de sons : %s", e)
    try:                                   # vrais enregistrements CC0 (Kenney) retravaillés
        from . import sfxdesign
        return sfxdesign.build(fam)
    except Exception as e:                  # fichiers manquants… → son synthétisé
        log.info("bruitage %s : son de secours (%s)", fam, e)
        return _synth(fam)


# --------------------------------------------------------------------------- rendu

def mix(col, k: float, to=(255, 255, 255)):
    return tuple(int(c + (t - c) * k) for c, t in zip(col, to))


def hue_tint(im: Image.Image, col) -> Image.Image:
    """Recolore une image (même luminosité et saturation, nouvelle teinte) : Kamehameha bleu → Final Flash jaune."""
    import colorsys
    h = colorsys.rgb_to_hsv(*[c / 255 for c in col])[0]
    _, S_, V_ = im.convert("RGB").convert("HSV").split()
    out = Image.merge("HSV", (Image.new("L", im.size, int(h * 255)), S_, V_)).convert("RGBA")
    out.putalpha(im.getchannel("A"))
    return out


STAGE_NAMES = {"ssj": "Super Saiyan", "ssj1": "Super Saiyan", "ssj2": "Super Saiyan 2", "ssj3": "Super Saiyan 3",
               "ssjgod": "Super Saiyan God", "ssjblue": "Super Saiyan Blue", "ssgss": "Super Saiyan Blue",
               "ui": "Ultra Instinct Sign", "uisign": "Ultra Instinct Sign", "ssj4": "Super Saiyan 4"}


def form_stages(value: str | None, n: int = 3) -> list[tuple[str, Path]]:
    """Formes intermédiaires (pendant le combat, avant le secret) : images du dossier `form:` sauf la 1re (base)
    et la dernière (secret), `n` au plus, réparties. → [(nom affiché, image)]."""
    if not value:
        return []
    p = (library.root() / value.strip().replace("\\", "/")).resolve()
    if not p.is_dir():
        return []
    imgs = fusion.chain_images(p.name) if p.parent.name == "_fusion" else \
        sorted(x for x in p.iterdir() if x.suffix.lower() in fusion.IMG_EXT)
    mid = imgs[1:-1]
    if len(mid) > n:
        mid = [mid[round(i * (len(mid) - 1) / max(1, n - 1))] for i in range(n)]
    out = []
    for x in mid:
        stem = re.sub(r"^\d+[\s._-]*", "", x.stem).strip()
        out.append((STAGE_NAMES.get(re.sub(r"[^a-z0-9]", "", stem.lower()), stem.upper()), x))
    return out


def form_image(value: str | None) -> Path | None:
    """« form: » d'une fiche → image : dossier _fusion (dernière forme), dossier/fichier de library/, ou perso."""
    if not value:
        return None
    from . import battle
    p = (library.root() / value.strip().replace("\\", "/")).resolve()
    if p.is_dir():
        if p.parent.name == "_fusion":
            imgs = fusion.chain_images(p.name)
        else:
            imgs = sorted(x for x in p.iterdir() if x.suffix.lower() in fusion.IMG_EXT)
        return imgs[-1] if imgs else None
    if p.is_file() and p.suffix.lower() in fusion.IMG_EXT:
        return p
    found = battle.fighters_from_library([value.strip()])
    return Path(found[0]["image_path"]) if found else None


def _summon_icon(name: str, color: tuple) -> Image.Image:
    from . import battle
    for p in movesets.folder().glob("*"):
        if p.stem.lower() == name.lower() and p.suffix.lower() in fusion.IMG_EXT:
            return fusion.icon(str(p), 256, color)
    found = battle.fighters_from_library([name])
    if found:
        return fusion.icon(found[0]["image_path"], 256, color)
    im = fusion.icon(None, 256, mix(color, 0.35, (0, 0, 0)))
    ImageDraw.Draw(im).text((128, 128), name[:1].upper(), font=render.font(150), anchor="mm", fill=(255, 255, 255))
    return im


CLIP_EXT = (".mp4", ".gif", ".webm", ".mov", ".mkv")


def clip_for(name: str) -> Path | None:
    """Clip / GIF optionnel joué pendant la cinématique de transformation :
    library/_domain/clips/« <Perso> secret.mp4 » (ou .gif…), sinon « <Prénom> secret »."""
    d = library.root() / "_domain" / "clips"
    if not d.is_dir():
        return None
    want = {f"{name} secret".lower(), name.lower()} | {f"{w} secret".lower() for w in name.split()}
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix.lower() in CLIP_EXT and p.stem.lower() in want:
            return p
    return None


def eye_band(name: str, image_path: str | None, W: int) -> Image.Image | None:
    """Bandeau des yeux pour le cut-in d'une attaque (fiche « eyes: Amaterasu ») : image « Eyes » de
    library/_domain/cine/<Perso>/ si elle existe, sinon découpé dans le visage du perso (bande des yeux)."""
    root = library.root() / "_domain" / "cine"
    keys = {name.lower()} | {w.lower() for w in name.split() if len(w) >= 3}
    d = next((p for p in sorted(root.iterdir()) if p.is_dir() and p.name.lower() in keys), None) \
        if root.is_dir() else None
    eyes = [p for p in sorted(d.iterdir()) if p.is_file() and re.search(r"eye", p.stem, re.I)] if d else []
    cw = int(W * 1.1)
    if eyes:
        im = Image.open(eyes[0]).convert("RGBA")
        im = im.crop(im.getchannel("A").getbbox() or (0, 0, im.width, im.height))
        return im.resize((cw, max(2, int(im.height * cw / im.width))), Image.LANCZOS)
    cands = [Path(image_path)] if image_path and Path(image_path).is_file() else []
    first = name.split()[0].lower() if name.split() else ""
    for d1 in (x for x in library.root().iterdir() if x.is_dir() and not x.name.startswith("_")) \
            if library.root().is_dir() else []:            # images du perso dans la bibliothèque (plus nettes)
        for d2 in (x for x in d1.iterdir() if x.is_dir() and x.name.lower().split()[:1] == [first]):
            cands += [p for p in d2.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")][:6]
    best = None                                         # (largeur du visage, image, x0, y0, x1, y1 de la bande)
    for p in cands:
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            continue
        w, h = im.size
        vb = faces.vision_box(p) if faces.vision_box is not None else None
        if vb:
            fx0, fy0, fw, fh = vb[0] * w, vb[1] * h, (vb[2] - vb[0]) * w, (vb[3] - vb[1]) * h
            ey = fy0 + fh * 0.45                         # les yeux : un peu au-dessus du milieu du visage
        else:
            f = faces.detect(im)
            if not f:
                continue
            fx0, fy0, fw, fh = f
            ey = fy0 + fh * 0.33
        bw, bh = fw * 1.7, fw * 0.42
        cx = fx0 + fw / 2
        box = (int(max(0, cx - bw / 2)), int(max(0, ey - bh / 2)), int(min(w, cx + bw / 2)), int(min(h, ey + bh / 2)))
        if best is None or fw > best[0]:
            best = (fw, im, box)
    if best is None:
        return None
    band = best[1].crop(best[2]).convert("RGBA")
    band = band.resize((cw, max(2, int(band.height * cw / band.width))), Image.LANCZOS)
    h = band.height                                       # bords haut/bas fondus
    ramp = [int(255 * min(1.0, min(y, h - 1 - y) / (h * 0.12))) for y in range(h)]
    mask = Image.new("L", (1, h))
    mask.putdata(ramp)
    band.putalpha(mask.resize((cw, h)))
    return band


def cine_layers(name: str, W: int, H: int) -> dict:
    """Couches d'une cinématique « carte » : library/_domain/cine/<Perso>/ (ou dossier au prénom / nom).
    Fichiers reconnus à leur nom : « BG » = fond, « Chara » = perso (le 1er), « Effect » = effets (12 max).
    Toutes les couches d'une même carte ont la même taille → elles se superposent pile."""
    root = library.root() / "_domain" / "cine"
    if not root.is_dir():
        return {}
    keys = {name.lower()} | {w.lower() for w in name.split() if len(w) >= 3}
    d = next((p for p in sorted(root.iterdir()) if p.is_dir() and p.name.lower() in keys), None)
    if d is None:
        return {}
    files = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in (".png", ".webp", ".jpg", ".jpeg"))
    bg = [p for p in files if re.search(r"(^|[_ -])bg", p.stem, re.I)]
    chara = sorted((p for p in files if re.search(r"chara", p.stem, re.I)),
                   key=lambda p: [int(x) for x in re.findall(r"\d+", p.stem)] or [0])   # Chara1 < Chara 2
    aura = [p for p in files if re.search(r"aura", p.stem, re.I)]
    cut = [p for p in files if re.search(r"cut|popup|pop", p.stem, re.I)]
    eff = [p for p in files if re.search(r"effect|fx", p.stem, re.I)]
    if not chara and not eff and not cut:
        return {}
    if len(eff) > 12:
        eff = [eff[int(i * len(eff) / 12)] for i in range(12)]
    out = {"effects": []}
    box_w, box_h = W, int(H * 0.72)
    ref = None

    def fit(p):
        nonlocal ref
        im = _prep_sprite(Image.open(p), crop=False, solid=bool(re.search(r"chara", p.stem, re.I)))
        if re.search(r"chara", p.stem, re.I) and im.getchannel("A").getextrema()[0] >= 250:
            m = Image.new("L", im.size, 0)                # capture d'écran (fond non détourable) : bords fondus
            ImageDraw.Draw(m).ellipse((-im.width * 0.1, im.height * 0.08, im.width * 1.1, im.height * 0.92), fill=255)
            im.putalpha(m.filter(ImageFilter.GaussianBlur(min(im.size) * 0.08)))
        if ref is None:
            ref = min(box_w / im.width, box_h / im.height)
        return im.resize((max(2, int(im.width * ref)), max(2, int(im.height * ref))), Image.LANCZOS)
    if chara:                                           # 2 images « Chara » : la 1re puis flash → la dernière
        out["chara"] = fit(chara[-1])
        if len(chara) > 1:
            c0 = _prep_sprite(Image.open(chara[0]), crop=False, solid=True)
            c0 = c0.crop(c0.getchannel("A").getbbox() or (0, 0, c0.width, c0.height))
            sc0 = out["chara"].height / c0.height
            out["chara0"] = c0.resize((max(2, int(c0.width * sc0)), out["chara"].height), Image.LANCZOS)
    if aura:                                            # aura du perso (derrière lui, plus grande)
        a_ = _prep_sprite(Image.open(aura[0]), crop=False)
        a_ = a_.crop(a_.getchannel("A").getbbox() or (0, 0, a_.width, a_.height))
        hh = int((out["chara"].height if "chara" in out else box_h) * 1.05)
        out["aura"] = a_.resize((max(2, int(a_.width * hh / a_.height)), hh), Image.LANCZOS)
    if cut:                                             # « cut-in » : bandeau avec les yeux qui traverse l'écran
        c_ = _key_dominant(Image.open(cut[0]))
        c_ = _prep_sprite(c_, crop=False)
        c_ = c_.crop(c_.getchannel("A").getbbox() or (0, 0, c_.width, c_.height))
        cw = int(W * 1.1)
        out["cutin"] = c_.resize((cw, max(2, int(c_.height * cw / c_.width))), Image.LANCZOS)
    for p in eff:
        try:
            out["effects"].append(fit(p))
        except Exception:
            pass
    if bg:
        b = Image.open(bg[0]).convert("RGBA")
        sc = max(W / b.width, H / b.height)
        b = b.resize((int(b.width * sc) + 1, int(b.height * sc) + 1), Image.LANCZOS)
        b = b.crop(((b.width - W) // 2, (b.height - H) // 2, (b.width - W) // 2 + W, (b.height - H) // 2 + H))
        out["bg"] = Image.blend(b, Image.new("RGBA", (W, H), (0, 0, 0, 255)), 0.25)
    hgt = (out.get("chara") or (out["effects"][0] if out["effects"] else None))
    out["y"] = (H - (hgt.height if hgt else box_h)) / 2 + H * 0.02
    return out


STYLES = [   # mot dans le nom de l'attaque → style d'effets (particules texturées)
    (r"hollow purple|\bpurple\b|murasaki", "purple"),          # Gojo (Limitless) : Violet = Bleu + Rouge
    (r"reversal|\bred\b|\baka\b", "red"),                      # Rouge = répulsion
    (r"lapse|\bao\b", "blue"),                                  # Bleu = attraction
    (r"unlimited void|muryokusho", "void"),                    # Extension du territoire de Gojo
    (r"chidori|kirin|raikiri|lightning|thunder|lightning|electr|kashimo|zeus|raiton", "lightning"),
    (r"rasengan|rasenshuriken|spiral|vortex|tornado", "spiral"),
    (r"amaterasu|black flame|blackflame|enton", "blackfire"),
    (r"fire|katon|flame|blaze|inferno|hinokami", "fire"),
]


STYLE_COL = {"purple": (175, 70, 255), "red": (255, 45, 60), "blue": (45, 125, 255)}   # couleur imposée


def style_of(name: str | None) -> str | None:
    n = (name or "").lower()
    for pat, st in STYLES:
        if re.search(pat, n):
            return st
    return None


def voice_file(name: str) -> Path | None:
    """Fichier son d'une réplique (« Narutooooo ») cherché par son nom dans library/_sfx/ et library/_sounds/."""
    want = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    if not want:
        return None
    for d in (library.root() / "_sfx", library.root() / "_sounds"):
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.suffix.lower() in fusion.SOUND_EXT and \
                        want in re.sub(r"[^a-z0-9]", "", p.stem.lower()):
                    return p
    return None


def next_episode() -> int:
    """Numéro du prochain épisode « DOMAIN WAR #N » : plus grand numéro déjà sorti + 1 (vidéos et archives),
    ou `slides.domain.episode_start` (config) pour démarrer la série à un numéro donné."""
    nums = []
    for d in (out_dir(), config.data_dir() / "archive" / "fusion"):
        if d.is_dir():
            for j in d.glob("domain_*.json"):
                try:
                    m = json.loads(j.read_text(encoding="utf-8"))
                except ValueError:
                    continue
                if m.get("episode"):
                    nums.append(int(m["episode"]))
    start = int(config.get()["slides"].get("domain", {}).get("episode_start", 3))
    return max([start - 1] + nums) + 1


def _log_sprite(size: int) -> Image.Image:
    """Bûche de la permutation (Kawarimi) dessinée à la main : tronc brun, cernes, liens."""
    w, h = max(8, size), max(4, int(size * 0.42))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=(120, 78, 42, 255), outline=(60, 36, 18, 255),
                        width=max(1, h // 10))
    for i in range(3):
        y = h * (0.3 + 0.2 * i)
        d.line((h * 0.6, y, w - h * 0.9, y + h * 0.05), fill=(90, 56, 28, 255), width=max(1, h // 14))
    d.ellipse((w - h, 0, w - 1, h - 1), fill=(196, 150, 96, 255), outline=(60, 36, 18, 255), width=max(1, h // 10))
    d.ellipse((w - h * 0.75, h * 0.25, w - h * 0.25, h * 0.75), outline=(140, 98, 58, 255), width=max(1, h // 12))
    return im


_SCORCH: list = []


def _scorch_sprite() -> Image.Image:
    """Cratère / brûlure (dessiné une fois) : tache sombre dégradée + fissures."""
    if _SCORCH:
        return _SCORCH[0]
    import numpy as np
    n = 256
    yy, xx = np.mgrid[0:n, 0:n] / (n / 2) - 1
    d = np.sqrt(xx ** 2 + yy ** 2)
    a = np.clip(1 - d, 0, 1) ** 0.8 * 200
    im = Image.fromarray(np.dstack([np.full((n, n), 18), np.full((n, n), 14), np.full((n, n), 14),
                                    a]).astype(np.uint8), "RGBA")
    dr = ImageDraw.Draw(im)
    rr = random.Random(5)
    for _ in range(9):                                  # fissures
        an, L, x, y = rr.uniform(0, 6.28), n * 0.45, n / 2, n / 2
        pts = [(x, y)]
        for _ in range(5):
            an += rr.uniform(-0.5, 0.5)
            x, y = x + math.cos(an) * L / 5, y + math.sin(an) * L / 5
            pts.append((x, y))
        dr.line(pts, fill=(8, 6, 6, 230), width=3)
    dr.ellipse((n * 0.3, n * 0.3, n * 0.7, n * 0.7), fill=(10, 8, 8, 160))
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    _SCORCH.append(im)
    return im


def clip_window(value: str | None, default=(0.0, 4.0)) -> tuple[float, float]:
    """Ligne de fiche « clip: 2-6 » → (départ, durée) en secondes (6 s max)."""
    try:
        a, _, b = str(value or "").replace(",", ".").partition("-")
        start = max(0.0, float(a))
        return start, min(6.0, max(0.5, float(b) - start))
    except ValueError:
        return default


SPRITE_EXT = (".png", ".webp", ".gif", ".jpg", ".jpeg")
_sprites: dict = {}


def fx_sprite(move: str | None, fighter: str | None = None, slot: str | None = None,
              sub: str | None = None) -> Image.Image | None:
    """Image d'une attaque : library/_domain/fx/« <Attaque>.png » (ex. Kamehameha.png), sinon « <Perso> <emplacement> ».
    PNG transparent conseillé ; une image sur fond blanc est détourée (le blanc devient transparent).
    Rayons : dessinés de gauche (départ) à droite (tête). `sub` = sous-dossier d'une forme (ex. « Ultra Instinct »)."""
    d = library.root() / "_domain" / "fx"
    if sub:
        d = d / sub
    want = [w.lower() for w in [move, f"{fighter} {slot}" if fighter and slot else None,
                                f"{fighter.split()[-1]} {slot}" if fighter and slot and fighter.split() else None] if w]
    key = (str(d),) + tuple(want)
    if key in _sprites:
        return _sprites[key]
    im = None
    if d.is_dir() and want:
        import difflib

        def nm(x):
            return re.sub(r"[^a-z0-9]", "", x.lower())
        files = [p for p in sorted(d.iterdir()) if p.is_file() and p.suffix.lower() in SPRITE_EXT]
        hit = next((p for w in want for p in files if p.stem.lower() == w), None)
        if hit is None:                                  # tolérant : « Rasenshukiren » = Rasenshuriken
            for w in want:
                close = difflib.get_close_matches(nm(w), [nm(p.stem) for p in files], 1, 0.84)
                if close:
                    hit = next(p for p in files if nm(p.stem) == close[0])
                    break
        if hit is not None:
            try:
                im = _prep_sprite(Image.open(hit))
            except Exception as e:
                log.info("image d'attaque %s illisible (%s)", hit.name, e)
    _sprites[key] = im
    return im


def _prep_sprite(im: Image.Image, crop: bool = True, solid: bool = False) -> Image.Image:
    """Détourage. Énergie (défaut) : alpha selon l'écart au fond (lueurs). `solid` = perso / objet opaque : seul le
    fond blanc relié au bord devient transparent (la peau, la chemise blanche… restent)."""
    im = im.convert("RGBA")
    a = im.getchannel("A")
    if a.getextrema()[0] >= 250:                        # pas de transparence → on détoure le fond
        import numpy as np
        from scipy import ndimage
        px = np.asarray(im).astype(np.float32)
        rgb = px[..., :3]
        border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        if solid:
            hi, lo = rgb.max(axis=2), rgb.min(axis=2)
            white = ((hi - lo) < 14) & (lo > 232)
            lab, _ = ndimage.label(white)
            edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
            alpha = np.where(np.isin(lab, list(edge)), 0, 255).astype(np.float32)
            alpha = ndimage.uniform_filter(alpha, 3)
            im = Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")
            if not crop:
                return im
            box = im.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
            return im.crop(box) if box else im
        bmean = float(border.max(axis=1).mean())
        if bmean < 115:                                  # fond SOMBRE (éclairs, énergie sur noir) : alpha = luminosité
            hi = rgb.max(axis=2)
            alpha = np.clip((hi - bmean * 1.15 - 10) * 2.2, 0, 255)
            k = np.maximum(alpha, 1)[..., None] / 255.0
            col = np.clip(rgb / k, 0, 255)
            im = Image.fromarray(np.dstack([col, alpha]).astype(np.uint8), "RGBA")
            if not crop:
                return im
            box = im.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
            return im.crop(box) if box else im
        hi, lo = rgb.max(axis=2), rgb.min(axis=2)
        grey = ((hi - lo) < 22) & (lo > 150)            # blanc / gris clair / faux damier « transparent »
        lab, _ = ndimage.label(grey)
        edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
        bg = np.isin(lab, list(edge))                   # fond = zones grises reliées au bord
        lum = rgb.mean(axis=2)
        if (~bg).any() and float(lum[~bg].mean()) < 110:  # sujet SOMBRE sur fond clair (flammes noires d'Amaterasu)
            alpha = np.clip((235 - lum) * 1.5, 0, 255)  # : l'encre noire reste, tout le clair devient transparent
            alpha[bg] = 0
            alpha = ndimage.uniform_filter(alpha, 3)
            col = np.clip(rgb * 0.55, 0, 255)
            im = Image.fromarray(np.dstack([col, alpha]).astype(np.uint8), "RGBA")
            if not crop:
                return im
            box = im.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
            return im.crop(box) if box else im
        alpha = np.clip((255 - lo) * 1.6, 0, 255)       # lueur colorée : alpha selon l'écart au blanc
        alpha[grey & ~bg] = 255                         # cœur blanc entouré d'énergie : opaque
        alpha[bg] = 0
        hole = ndimage.binary_fill_holes(alpha > 200) & (alpha <= 200) & ~bg
        alpha[hole] = 255                               # cœur clair entouré d'énergie : opaque
        grey = grey | hole
        alpha = ndimage.uniform_filter(alpha, 3)         # bords doux
        k = np.maximum(alpha, 1)[..., None] / 255.0
        col = np.where((grey & ~bg)[..., None], rgb, np.clip(255 - (255 - rgb) / k, 0, 255))
        im = Image.fromarray(np.dstack([col, alpha]).astype(np.uint8), "RGBA")
    if not crop:
        return im
    box = im.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
    return im.crop(box) if box else im


def _key_dominant(im: Image.Image) -> Image.Image:
    """Cut-in sur fond uni lumineux (ex. yeux de Naruto sur chakra jaune) : la couleur dominante devient
    transparente, il reste les yeux. Image déjà transparente ou sans fond dominant : inchangée."""
    import numpy as np
    im = im.convert("RGBA")
    if im.getchannel("A").getextrema()[0] < 250:
        return im
    a = np.asarray(im).astype(np.float32)[..., :3]
    med = np.median(a.reshape(-1, 3), axis=0)
    d = np.sqrt(((a - med) ** 2).sum(2))
    if float((d < 25).mean()) < 0.45 or float(med.mean()) < 150:
        return im
    alpha = np.clip((d - 40) * 4, 0, 255)
    return Image.fromarray(np.dstack([a, alpha]).astype(np.uint8), "RGBA")


def _union_crop(frames: list) -> list:
    """Recadre toutes les images d'une animation sur la même boîte (sinon elle tremble)."""
    boxes = [f.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox() for f in frames]
    boxes = [b for b in boxes if b]
    if not boxes:
        return []
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    return [f.crop(box) for f in frames]


def paste_beam(img: Image.Image, spr: Image.Image, x1, y1, x2, y2, width: float, alpha: float = 1.0) -> None:
    """Colle l'image d'un rayon étirée de (x1, y1) à (x2, y2)."""
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 4 or width < 2:
        return
    rs = Image.NEAREST if spr.info.get("pixel") else Image.BILINEAR      # pixel-art : pas de flou
    s = spr.resize((max(2, int(L)), max(2, int(width))), rs)
    if alpha < 1:
        s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    s = s.rotate(-math.degrees(math.atan2(y2 - y1, x2 - x1)), expand=True, resample=rs)
    img.alpha_composite(s, (int((x1 + x2) / 2 - s.width / 2), int((y1 + y2) / 2 - s.height / 2)))


def paste_center(img: Image.Image, spr: Image.Image, x, y, size: float, alpha: float = 1.0, angle: float = 0) -> None:
    if size < 3:
        return
    r = size / max(spr.width, spr.height)
    rs = Image.NEAREST if spr.info.get("pixel") else Image.BILINEAR      # pixel-art : pas de flou
    s = spr.resize((max(2, int(spr.width * r)), max(2, int(spr.height * r))), rs)
    if angle:
        s = s.rotate(-math.degrees(angle), expand=True, resample=rs)
    if alpha < 1:
        s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))


def clip_frames(path: Path, fps: int, w: int, h: int, max_s: float = 3.0, start: float = 0.0) -> list:
    """Images du clip (au plus `max_s` s), redimensionnées dans w×h (bandes noires si besoin)."""
    w, h = w // 2 * 2, h // 2 * 2
    try:
        r = subprocess.run([require_bin("ffmpeg"), "-loglevel", "error", "-ss", f"{start:.2f}", "-t", f"{max_s:.2f}",
                            "-i", str(path), "-vf",
                            f"fps={fps},scale={w}:{h}:force_original_aspect_ratio=decrease,"
                            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True, timeout=120)
    except Exception as e:
        log.info("clip %s illisible (%s)", path.name, e)
        return []
    n = len(r.stdout) // (w * h * 3)
    return [Image.frombytes("RGB", (w, h), r.stdout[i * w * h * 3:(i + 1) * w * h * 3]) for i in range(n)]


def _credits() -> list[str]:
    try:
        from . import sfxbank
        return sfxbank.credits()
    except Exception:
        return []


def generate(fighters: list[dict], seconds: float = 35, title: str | None = None, seed: int | None = None,
             tries: int = 10, out: Path | None = None, fps: int = 30, W: int = 1080, H: int = 1920,
             winner: int | None = None, comeback: bool = False, cine: str = "auto", sounds: str = "anime",
             underdog: int | None = None) -> Path:
    """`fighters` = 2 persos {name, image_path}. Leur fiche (attaques, secret, passif, forme) vient de movesets.
    Scénario : `winner` = 0 / 1 pour imposer le gagnant, `comeback` = il perd d'abord, sort son secret, puis gagne.
    `cine` : transformation en « auto » (cut-in/carte si library/_domain/cine/<Perso>/, sinon clip), « clip » (extrait de
    l'anime), « card » (jamais de clip : version YouTube sans Content ID)."""
    names = [f["name"] for f in fighters]
    sheets = [movesets.sheet_for(n) for n in names]
    cols = [hex_rgb(s.get("color"), TEAM[i]) for i, s in enumerate(sheets)]
    if sum((a - b) ** 2 for a, b in zip(*cols)) < 120 ** 2:      # 2 couleurs trop proches → bleu / rouge
        cols = list(TEAM)
    if seed is None:
        seed = pick_seed(seconds, W, H, sheets, tries, winner=winner, comeback=comeback, underdog=underdog)
    war, director = make(seed, seconds, W, H, sheets, winner)
    nx, ny, cell, ox, oy = geometry(W, H)
    m_ep = re.match(r"\s*domain war\s*#\s*(\d+)", title or "", re.I)
    episode = int(m_ep.group(1)) if m_ep else next_episode()
    title = title or f"DOMAIN WAR #{episode}"                    # série numérotée (demandé : « ce sont des épisodes »)
    from . import seo as _seo
    vs_line = f"{_seo.short(names[0])} vs {_seo.short(names[1])}".upper()
    k = W / 1080
    icons = [fusion.icon(f.get("image_path"), 256, cols[i]) for i, f in enumerate(fighters)]
    forms = []                                                   # icône après transformation (fiche « form: »)
    for i, sh in enumerate(sheets):
        fp = form_image(sh.get("form"))
        forms.append(fusion.icon(str(fp), 256, cols[i]) if fp else None)

    stages = [[(nm, fusion.icon(str(pth), 256, cols[i])) for nm, pth in
               form_stages(sh.get("form"), int(sh.get("stages") or 3))] for i, sh in enumerate(sheets)]
    stage = [-1, -1]                                             # forme intermédiaire actuelle (-1 = base)
    stage_t = [[seconds * (0.07 + 0.075 * j) + 1.3 * i for j in range(len(stages[i]))] for i in (0, 1)]
    stage_ev = []                                                # (t, équipe) pour le son
    fdir = []                                                    # effets propres à la forme secrète (UI…)
    for sh in sheets:
        sn = (sh.get("secret") or {}).get("name") or ""
        fdir.append(sn if sn and (library.root() / "_domain" / "fx" / sn).is_dir() else None)

    def face(team):
        if forms[team] is not None and war.transformed[team] is not None:
            return forms[team]
        return stages[team][stage[team]][1] if stage[team] >= 0 else icons[team]
    summons = {}
    icache: dict = {}

    def ic(key, base, d):
        kk = (key, int(d))
        if kk not in icache:
            icache[kk] = base.resize((max(4, int(d)), max(4, int(d))), Image.LANCZOS)
        return icache[kk]

    bg = Image.new("RGBA", (W, H), (10, 10, 18, 255))
    d0 = ImageDraw.Draw(bg)
    tf = render.font(int(64 * k))
    while tf.size > 30 and len(render.wrap(title.upper(), tf, int(W * 0.92), d0)) > 2:
        tf = render.font(tf.size - 4)
    y = int(H * 0.03)
    lines = render.wrap(title.upper(), tf, int(W * 0.92), d0)
    for line in lines:
        d0.text((W / 2, y), line, font=tf, anchor="ma", fill=(240, 242, 250), stroke_width=int(3 * k),
                stroke_fill=(0, 0, 0))
        y += int(sum(tf.getmetrics()) * 1.02)
    if len(lines) == 1:                                          # sous-titre : « NARUTO VS SASUKE » aux couleurs
        sf_ = render.font(int(46 * k))
        a_, b_ = vs_line.split(" VS ", 1) if " VS " in vs_line else (vs_line, "")
        wa, wv = render.text_width(d0, a_ + " ", sf_), render.text_width(d0, "VS ", sf_)
        x_ = W / 2 - (wa + wv + render.text_width(d0, b_, sf_)) / 2
        for txt, col in ((a_ + " ", mix(cols[0], 0.2)), ("VS ", (200, 200, 210)), (b_, mix(cols[1], 0.2))):
            d0.text((x_, y + 4 * k), txt, font=sf_, anchor="la", fill=col, stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
            x_ += render.text_width(d0, txt, sf_)

    out = out or out_dir() / f"domain_{seed}.mp4"
    tmp = out.with_suffix(".video.mp4")
    ffmpeg = require_bin("ffmpeg")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    banners, seen, frames, clash_shown, seen_sp = [], 0, 0, False, 0
    pf, nf, sf = render.font(int(56 * k)), render.font(int(42 * k)), render.font(int(30 * k))
    gw, gh = nx * cell, ny * cell
    pauses = []                                                  # (temps simu, durée) : cinématiques, arrêts, ralentis
    cine_at = []                                                 # (temps simu, durée) des cinématiques seules
    finish_at = []                                               # (temps simu, durée) du FINISH
    intro_hit = []                                               # instant du choc de l'accroche (vidéo)
    cine_done = [False, False]
    eyes_at = []                                                 # instants des cut-in des yeux (Amaterasu…)
    eyes_count: dict = {}
    eye_moves = [{m.strip().lower() for m in (sheets[i].get("eyes") or "").split(",") if m.strip()} for i in (0, 1)]
    eye_img = [eye_band(names[i], fighters[i].get("image_path"), W) if eye_moves[i] else None for i in (0, 1)]
    last_img = bg.copy()
    GOLD = (255, 214, 10)

    def cinematic(team: int, base: Image.Image) -> int:
        """Transformation : la simu s'arrête. 1) clip/GIF de l'anime s'il y en a un (library/_domain/clips/) ;
        2) cinématique « carte » si library/_domain/cine/<Perso>/ a des couches (BG, Chara, Effect…, ex. assets
        Dragon Ball Legends) : fond, effets qui pulsent et dérivent, le perso arrive en zoom ;
        sinon 3) l'icône : ancienne forme qui tremble → flash → nouvelle forme. Puis le nom de la forme."""
        sec = [e for e in director.events if e[1] == team and e[2] == "secret"]
        move = (sec[-1][3].get("name") if sec else "") or "TRANSFORMATION"
        cp = clip_for(names[team])
        cs, cd = clip_window(sheets[team].get("clip"))
        layers = {} if cine == "clip" and cp else cine_layers(names[team], W, H)
        cf = (clip_frames(cp, fps, int(W * 0.92), int(W * 0.92 * 9 / 16), cd, cs)       # « auto » : cut-in/carte > clip
              if cp and cine != "card" and not layers else [])
        n_card = int(fps * (3.4 if layers.get("chara0") is not None else 2.4)) \
            if layers.get("chara") is not None or layers.get("effects") else 0
        n_icon = int(fps * 1.8) if not cf and not layers else 0
        dark = Image.blend(base.convert("RGB"), Image.new("RGB", (W, H), (0, 0, 0)), 0.86).convert("RGBA")
        cx, cy = W / 2, H * 0.44
        rr = random.Random(int(war.t * 1000) + team)
        mfont = render.font(int(110 * k))
        dd = ImageDraw.Draw(dark)
        while mfont.size > 30 and render.text_width(dd, move.upper(), mfont) > W * 0.92:
            mfont = render.font(mfont.size - 4)

        def aura_bg(f, a):
            img = dark.copy()
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            gd = ImageDraw.Draw(gl)
            pulse = 1 + 0.06 * math.sin(f / fps * 30)
            R = W * (0.28 + 0.12 * min(1, a * 2)) * pulse
            gd.ellipse((cx - R, cy - R, cx + R, cy + R), fill=cols[team] + (150,))
            for i in range(18):                                 # rayons d'aura qui tournent
                an = i / 18 * 2 * math.pi + f / fps * 1.5
                L = W * (0.35 + 0.25 * rr.random()) * min(1, a * 3)
                gd.line((cx, cy, cx + math.cos(an) * L, cy + math.sin(an) * L), fill=mix(cols[team], 0.5) + (120,),
                        width=int(14 * k))
            img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(28 * k)))
            ld = ImageDraw.Draw(img)
            for _ in range(3):                                  # éclairs
                x0, y0 = cx + rr.uniform(-1, 1) * W * 0.4, cy + rr.uniform(-1, 1) * W * 0.4
                pts = [(x0, y0)]
                for _ in range(5):
                    x0 += rr.uniform(-60, 60) * k
                    y0 += rr.uniform(-60, 60) * k
                    pts.append((x0, y0))
                ld.line(pts, fill=mix(cols[team], 0.75), width=int(5 * k))
            return img, pulse

        def texts(img, show_move, since):
            ld = ImageDraw.Draw(img)
            ld.text((W / 2, H * 0.155), names[team].upper(), font=render.font(int(70 * k)), anchor="mm",
                    fill=mix(cols[team], 0.3), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            if show_move:
                pop = 1 + 0.35 * max(0.0, 1 - since / 0.25)
                ft = render.font(max(20, int(mfont.size * pop)))
                ld.text((W / 2, H * 0.84), move.upper(), font=ft, anchor="mm", fill=GOLD,
                        stroke_width=int(7 * k), stroke_fill=(0, 0, 0))

        def flash(img, fl):
            if fl > 0:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(230 * min(1.0, fl)))))

        def zoomed(im, z, cx_=None, cy_=None):
            """Zoom caméra : recadrage autour d'un point puis remise à la taille."""
            if z <= 1.001:
                return im
            cx_, cy_ = W / 2 if cx_ is None else cx_, H * 0.45 if cy_ is None else cy_
            w_, h_ = W / z, H / z
            x0_ = min(max(0, cx_ - w_ / 2), W - w_)
            y0_ = min(max(0, cy_ - h_ / 2), H - h_)
            return im.crop((int(x0_), int(y0_), int(x0_ + w_), int(y0_ + h_))).resize((W, H), Image.BILINEAR)

        out = 0
        mains_ = war.mains(team)
        if mains_ and (cf or layers or n_icon):                  # 0) entrée : la caméra fonce sur le perso
            bx_, by_ = ox + mains_[0]["x"], oy + mains_[0]["y"]
            n_in = int(fps * 0.3)
            for f in range(n_in):
                a = (f + 1) / n_in
                e = 1 - (1 - a) ** 3
                z = 1 + 2.2 * e
                w_, h_ = W / z, H / z
                x0_ = min(max(0, bx_ - w_ / 2), W - w_)
                y0_ = min(max(0, by_ - h_ / 2), H - h_)
                img = base.crop((int(x0_), int(y0_), int(x0_ + w_), int(y0_ + h_))).resize((W, H), Image.BILINEAR)
                if a > 0.3:                                      # flou radial approximatif : copies zoomées
                    for q in (1.03, 1.06, 1.1):
                        g_ = zoomed(img, q, W / 2, H / 2)
                        g_.putalpha(int(70 * (a - 0.3)))
                        img.alpha_composite(g_)
                flash(img, max(0.0, (a - 0.55) / 0.45))
                proc.stdin.write(img.convert("RGB").tobytes())
                out += 1
        for f, fr in enumerate(cf):                              # 1) clip de l'anime / GIF
            img, _ = aura_bg(f, f / max(1, len(cf) - 1))
            x, y = int(cx - fr.width / 2), int(cy - fr.height / 2)
            ImageDraw.Draw(img).rectangle((x - 6 * k, y - 6 * k, x + fr.width + 6 * k, y + fr.height + 6 * k),
                                          fill=cols[team])
            img.paste(fr, (x, y))
            texts(img, not layers, f / fps)
            flash(img, 1 - f / 3 if f < 3 else 0)
            proc.stdin.write(img.convert("RGB").tobytes())
            out += 1
        cut = layers.get("cutin")
        n_cut = int(fps * 1.1) if cut is not None else 0
        speed = fx_sprite("impact") or fx_sprite("burst")
        for f in range(n_cut):                                   # 2a) « cut-in » : les yeux traversent l'écran
            a, t_ = f / max(1, n_cut - 1), f / fps
            img = dark.copy()
            if speed is not None:                                # lignes de vitesse qui tournent derrière
                paste_center(img, speed, W / 2, H * 0.45, W * 1.9, 0.55, t_ * 0.8)
            slide = 1 - (1 - min(1.0, a / 0.22)) ** 3 if a < 0.75 else 1 + ((a - 0.75) / 0.25) ** 2 * 1.2
            x = W * (1.0 - slide) + (W - cut.width) / 2 - (a * 40 * k if a < 0.75 else 0)
            band = Image.new("RGBA", (W, cut.height + int(40 * k)), (0, 0, 0, 0))
            bd = ImageDraw.Draw(band)                             # bandeau sombre, liseré à la couleur du camp
            bd.polygon(((0, 30 * k), (W, 0), (W, band.height - 30 * k), (0, band.height)), fill=(8, 8, 14, 235))
            bd.line(((0, 30 * k), (W, 0)), fill=mix(cols[team], 0.3) + (255,), width=int(8 * k))
            bd.line(((0, band.height), (W, band.height - 30 * k)), fill=mix(cols[team], 0.3) + (255,), width=int(8 * k))
            img.alpha_composite(band, (int(x - (W - cut.width) / 2), int(H * 0.42 - band.height / 2)))
            img.alpha_composite(cut, (int(x), int(H * 0.42 - cut.height / 2)))
            texts(img, False, 0)
            flash(img, 1 - f / 3 if f < 3 else 0)
            proc.stdin.write(img.convert("RGB").tobytes())
            out += 1
        acol = hex_rgb(sheets[team].get("aura"), mix(cols[team], 0.3))
        ch = layers.get("chara")
        ch0 = layers.get("chara0")
        arrive = 0.55 if ch0 is not None else 0.22
        g_ring = list(vfxgen.frames("ring", 256, tuple(acol[:3]))) if n_card else []
        g_bolt = list(vfxgen.frames("lightning", 256, tuple(acol[:3]))) if n_card else []
        g_charge = list(vfxgen.frames("charge", 256, tuple(acol[:3]))) if n_card else []

        def ease_out(x, p=3):
            return 1 - (1 - min(1.0, max(0.0, x))) ** p

        def back_out(x):                                         # dépasse un peu puis revient (punch)
            x = min(1.0, max(0.0, x))
            c1, c3 = 1.70158, 2.70158
            return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

        def with_alpha(im, q):
            if q >= 0.99:
                return im
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v, q=q: int(v * q)))
            return im

        for f in range(n_card):                                  # 2b) cinématique « carte » (couches)
            a, t_ = f / max(1, n_card - 1), f / fps
            since = (a - arrive) * n_card / fps                  # secondes depuis l'éveil (négatif avant)
            pre = max(0.0, (arrive - a)) * n_card / fps          # secondes avant l'éveil
            push = 1 + 0.10 * ease_out(a, 1.5)                   # la caméra avance tout du long
            img = zoomed(layers["bg"].copy(), 1 + (push - 1) * 0.5) if layers.get("bg") else dark.copy()
            if not layers.get("bg") and speed is not None:
                paste_center(img, speed, W / 2, H * 0.47, W * 2.0 * (1 + 0.1 * a), 0.45, -t_ * 0.6)
            rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))     # rayons de lumière qui tournent derrière
            rd = ImageDraw.Draw(rays)
            ccx, ccy = W / 2, layers["y"] + (ch.height if ch is not None else H * 0.4) * 0.45
            ri = 0.18 + 0.5 * (min(1.0, since / 0.5) if since >= 0 else max(0.0, 1 - pre / 1.2) * 0.6)
            for i_ in range(14):
                an = i_ / 14 * 2 * math.pi + t_ * (0.6 if since < 0 else 1.6)
                pts = [(ccx, ccy), (ccx + math.cos(an - 0.06) * W * 1.3, ccy + math.sin(an - 0.06) * W * 1.3),
                       (ccx + math.cos(an + 0.06) * W * 1.3, ccy + math.sin(an + 0.06) * W * 1.3)]
                rd.polygon(pts, fill=acol + (int(90 * ri),))
            img.alpha_composite(rays)
            if ch0 is not None and a < arrive:                   # 1re forme : monte en fondu, puis tremble
                b0 = ease_out(a / 0.14)
                sh0 = math.sin(t_ * 70) * 9 * k * max(0.0, 1 - pre / 0.9)       # tremblement qui monte
                sq = 1 - 0.05 * max(0.0, 1 - pre / 0.12)                        # se tasse juste avant l'éveil
                c0 = ch0 if sq == 1 else ch0.resize((int(ch0.width * sq), int(ch0.height * sq)), Image.BILINEAR)
                c0 = with_alpha(c0, b0)
                img.alpha_composite(c0, (int((W - c0.width) / 2 + sh0),
                                         int(layers["y"] + (1 - b0) * 60 * k + (ch0.height - c0.height))))
            au = layers.get("aura")
            if au is not None and a >= arrive * 0.5:              # aura qui flambe derrière le perso
                b = ease_out((a - arrive * 0.5) / 0.15) * (0.45 if ch0 is not None and a < arrive else 1.0)
                grow = 1.0 if since < 0 else 1 + 0.25 * max(0.0, 1 - since / 0.4)
                for j, (sx, sy, q) in enumerate(((1.0, 1.0, 1.0), (1.08, 1.12, 0.45))):
                    fl = 1 + 0.05 * math.sin(t_ * 22 + j * 2)
                    w_, h_ = int(au.width * sx * fl * grow), int(au.height * sy * (2 - fl) * grow)
                    e = with_alpha(au.resize((w_, h_), Image.BILINEAR), b * q * (0.85 + 0.15 * math.sin(t_ * 17 + j)))
                    base_y = layers["y"] + (ch.height if ch is not None else au.height)
                    img.alpha_composite(e, (int((W - w_) / 2), int(base_y - h_ + 20 * k)))
            if since < 0 and g_charge and pre < 1.3:              # énergie qui converge vers le perso
                cf_ = g_charge[int(t_ * 24) % len(g_charge)]
                paste_center(img, cf_, ccx, ccy, W * 1.1 * (0.7 + 0.3 * (1 - pre / 1.3)), 0.9)
            effs = layers["effects"]
            for i, ef in enumerate(effs):                        # couches d'effets (éclairs roses…) qui pulsent
                a_i = 0.04 + 0.3 * i / max(1, len(effs))
                al = min(1.0, max(0.0, (a - a_i) / 0.12)) * (0.72 + 0.28 * math.sin(t_ * 9 + i * 1.7))
                if al <= 0.02:
                    continue
                e = with_alpha(ef, al)
                dx = math.sin(t_ * 2.2 + i) * 14 * k
                dy = math.cos(t_ * 1.8 + i * 0.7) * 14 * k - (i % 3) * t_ * 30 * k * (i % 2)
                img.alpha_composite(e, (int((W - e.width) / 2 + dx), int(layers["y"] + dy)))
            if ch is not None and a >= (arrive if ch0 is not None else arrive * 0.5):
                b = min(1.0, since / 0.35) if ch0 is not None else ease_out((a - arrive * 0.5) / (arrive * 0.5))
                sc = (1.6 - 0.6 * back_out(b)) if ch0 is not None else (1.25 - 0.25 * ease_out(b))
                c2 = ch if abs(sc - 1.0) < 0.005 else ch.resize((max(2, int(ch.width * sc)), max(2, int(ch.height * sc))),
                                                               Image.BILINEAR)
                c2 = with_alpha(c2, min(1.0, b * 3))
                fy = math.sin(t_ * 3) * 6 * k
                img.alpha_composite(c2, (int((W - c2.width) / 2), int(layers["y"] + (ch.height - c2.height) / 2 + fy)))
            if 0 <= since < 0.6 and g_ring:                       # onde de choc + éclairs à l'éveil
                rf = g_ring[min(len(g_ring) - 1, int(since / 0.6 * len(g_ring)))]
                paste_center(img, rf, ccx, ccy, W * (0.6 + 2.2 * since), 1.0)
            if 0 <= since < 0.9 and g_bolt:
                bf_ = g_bolt[int(t_ * 24) % len(g_bolt)]
                paste_center(img, bf_, ccx, ccy, W * 1.3, min(1.0, (0.9 - since) / 0.3), rr.uniform(0, 6.28))
            strobe = since < 0 and pre < 0.28 and int(f) % 2 == 0   # stroboscope juste avant l'éveil
            img = zoomed(img, push, W / 2, ccy)
            amp = 0
            if since >= 0:
                amp = 22 * k * max(0.0, 1 - since / 0.7)
            elif pre < 0.9:
                amp = 10 * k * (1 - pre / 0.9)
            if amp > 0.5:
                rb = random.Random(f + team * 97)
                sh_img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
                sh_img.alpha_composite(img, (int(rb.uniform(-amp, amp)), int(rb.uniform(-amp, amp))))
                img = sh_img
            if 0 <= since < 0.2:
                img = fxengine.chroma(img, int(8 * k * (1 - since / 0.2)))
            if 0.06 <= since < 0.06 + 2.2 / fps:                   # 2 « impact frames » à 2 tons
                img = fxengine.impact_frame(img, acol, invert=int(since * fps) % 2 == 1)
            texts(img, since >= 0, since)
            end_in = (1 - a) * n_card / fps
            if end_in < 0.22:                                     # sortie : la caméra fonce + flash
                img = zoomed(img, 1 + 0.5 * (1 - end_in / 0.22) ** 2, W / 2, ccy)
            flash(img, (1 - since / 0.08) if 0 <= since < 0.08 else (0.45 if strobe else (1 - f / 3 if f < 3 else 0)))
            if end_in < 0.12:
                flash(img, 1 - end_in / 0.12)
            proc.stdin.write(img.convert("RGB").tobytes())
            out += 1
        for f in range(n_icon):                                  # 3) l'icône seule
            a = f / max(1, n_icon - 1)
            img, pulse = aura_bg(f, a)
            morph = 0.42                                        # ancienne forme qui tremble → flash → nouvelle forme
            if a < morph:
                sz = int(W * (0.42 + 0.06 * a / morph))
                sh = rr.uniform(-1, 1) * 10 * k * (a / morph)
                im = (stages[team][stage[team]][1] if stage[team] >= 0 else icons[team]).resize((sz, sz), Image.LANCZOS)
            else:
                b2 = (a - morph) / (1 - morph)
                sz = int(W * (0.5 + 0.12 * (1 - (1 - min(1, b2 * 2.5)) ** 3)) * pulse)
                sh = 0
                im = (forms[team] or icons[team]).resize((sz, sz), Image.LANCZOS)
            img.alpha_composite(im, (int(cx - sz / 2 + sh), int(cy - sz / 2)))
            texts(img, a > morph, (a - morph) * n_icon / fps)
            flash(img, (1 - (a - 0.42) / 0.1) if 0.42 <= a < 0.52 else (1 - f / 3 if f < 3 else 0))
            proc.stdin.write(img.convert("RGB").tobytes())
            out += 1
        pauses.append((war.t, out / fps))
        cine_at.append((war.t, out / fps))
        return out

    def eye_cut(team: int, base: Image.Image, move: str) -> int:
        """Cut-in des yeux façon Naruto Storm (avant Amaterasu, Tsukuyomi…) : le combat se fige, le bandeau des
        yeux traverse l'écran, ils s'illuminent en rouge (flash), nom de l'attaque, puis ça repart. ~0,9 s."""
        band = eye_img[team]
        if band is None:
            return 0
        n = int(fps * 0.9)
        dark = Image.blend(base.convert("RGB"), Image.new("RGB", (W, H), (0, 0, 0)), 0.82).convert("RGBA")
        ec = STYLE_COL.get(style_of(move), (255, 60, 60))       # Sharingan = rouge ; Six Eyes (Purple) = violet
        red = Image.merge("RGBA", tuple(band.getchannel(ch).point(lambda v, c_=c_: min(255, int(v * 0.35 + c_ * 0.55)))
                                        for ch, c_ in zip("RGB", ec)) + (band.getchannel("A"),))
        speed = fx_sprite("impact") or fx_sprite("burst")
        ft = render.font(int(96 * k))
        dd = ImageDraw.Draw(dark)
        while ft.size > 30 and render.text_width(dd, move.upper(), ft) > W * 0.9:
            ft = render.font(ft.size - 4)
        cy = H * 0.42
        rr = random.Random(int(war.t * 1000) + 7 * team)
        out = 0
        for f in range(n):
            a, t_ = f / max(1, n - 1), f / fps
            img = dark.copy()
            if speed is not None:
                paste_center(img, speed, W / 2, cy, W * 1.9, 0.5, -t_ * 1.2)
            if a < 0.16:                                     # entre par la droite, freine
                x = W * (1 - a / 0.16) ** 3
            elif a < 0.86:
                x = -(a - 0.16) * 50 * k
            else:                                            # repart à gauche
                x = -(0.70 * 50 * k) - W * 1.2 * ((a - 0.86) / 0.14) ** 2
            x += (W - band.width) / 2
            sh = rr.uniform(-1, 1) * 8 * k if 0.35 <= a < 0.55 else 0
            bar = Image.new("RGBA", (W, band.height + int(36 * k)), (0, 0, 0, 230))
            ImageDraw.Draw(bar).rectangle((0, 0, W, int(6 * k)), fill=mix(cols[team], 0.3) + (255,))
            ImageDraw.Draw(bar).rectangle((0, bar.height - int(6 * k), W, bar.height), fill=mix(cols[team], 0.3) + (255,))
            img.alpha_composite(bar, (0, int(cy - bar.height / 2)))
            glow = min(1.0, max(0.0, (a - 0.35) / 0.12))
            b_ = band if glow <= 0 else Image.blend(band, red, 0.55 * glow)
            img.alpha_composite(b_, (int(x + sh), int(cy - band.height / 2 + sh)))
            if glow > 0:                                     # lueur rouge sur les yeux
                gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(gl).rectangle((0, cy - band.height * 0.3, W, cy + band.height * 0.3),
                                             fill=(255, 30, 30, int(70 * glow)))
                img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(30 * k)))
            if a >= 0.35:
                since = (a - 0.35) * n / fps
                pop = 1 + 0.4 * max(0.0, 1 - since / 0.15)
                f2 = render.font(max(20, int(ft.size * pop)))
                ImageDraw.Draw(img).text((W / 2, cy + band.height / 2 + 110 * k), move.upper(), font=f2,
                                         anchor="mm", fill=mix(ec, 0.15), stroke_width=int(7 * k),
                                         stroke_fill=(0, 0, 0))
            if 0.35 <= a < 0.42:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - (a - 0.35) / 0.07)))))
            proc.stdin.write(img.convert("RGB").tobytes())
            out += 1
        pauses.append((war.t, out / fps))
        eyes_at.append((war.t, team))
        return out

    def intro() -> int:
        """Accroche (1re seconde) : les 2 persos foncent l'un sur l'autre, choc au centre (flash, éclairs), « VS »,
        « WHO WINS? ». Pas de pause dans le combat ensuite : ça enchaîne direct."""
        n = int(fps * 1.5)                                       # 1,5 s : le temps de lire « Like & Follow »
        hit_at = 0.32
        spd = fxengine.TexFX(seed + 5)
        burst = spd.tinted("star_09", (255, 250, 230), 1.0)
        lines = spd.tinted("trace_02", (255, 255, 255), 1.0)
        base = Image.new("RGBA", (W, H), (8, 8, 14, 255))
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        gd.polygon(((0, 0), (W * 0.62, 0), (W * 0.38, H), (0, H)), fill=cols[0] + (110,))
        gd.polygon(((W * 0.62, 0), (W, 0), (W, H), (W * 0.38, H)), fill=cols[1] + (110,))
        base.alpha_composite(g.filter(ImageFilter.GaussianBlur(40 * k)))
        sz = int(W * 0.5)
        ics = [icons[i].resize((sz, sz), Image.LANCZOS) for i in (0, 1)]
        vsf = render.font(int(190 * k))
        wf = render.font(int(92 * k))
        nfnt = render.font(int(56 * k))
        rr = random.Random(seed)
        for f in range(n):
            a = f / fps
            img = base.copy()
            if lines is not None:                                # lignes de vitesse qui défilent
                for j in range(14):
                    y = (rr.random() * H + a * 2600 * k * (1 if j % 2 else -1)) % H
                    x = rr.random() * W
                    paste_center(img, lines, x, y, 70 * k, 0.35, 90)
            p = min(1.0, a / hit_at)
            e = 1 - (1 - p) ** 3                                 # arrivée rapide puis choc
            cyy = H * 0.42
            shake = (math.sin(a * 80) * 14 * k * max(0.0, 1 - (a - hit_at) / 0.4)) if a >= hit_at else 0
            # 1re image = couverture TikTok/YouTube : les 2 visages déjà bien visibles (pas un écran vide),
            # puis ils reculent un peu et foncent l'un sur l'autre
            x0 = (W * 0.5 - sz * 0.92) - sz * 0.25 * (1 - e)
            x1 = (W * 0.5 + sz * 0.08) + sz * 0.25 * (1 - e)
            img.alpha_composite(ics[0], (int(x0 + shake), int(cyy - sz / 2 - 60 * k)))
            img.alpha_composite(ics[1], (int(x1 - shake), int(cyy - sz / 2 + 60 * k)))
            d = ImageDraw.Draw(img)
            if a < hit_at:                                       # couverture : « VS » + noms dès la 1re image
                d.text((W / 2, cyy + 10 * k), "VS", font=vsf, anchor="mm", fill=GOLD, stroke_width=int(10 * k),
                       stroke_fill=(0, 0, 0))
                hw0 = render.text_width(d, names[0].upper(), nfnt) / 2 + 20 * k   # le nom reste dans l'écran
                hw1 = render.text_width(d, names[1].upper(), nfnt) / 2 + 20 * k
                d.text((max(hw0, x0 + sz / 2), cyy + sz / 2 - 40 * k), names[0].upper(), font=nfnt, anchor="mm",
                       fill=mix(cols[0], 0.3), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                d.text((min(W - hw1, x1 + sz / 2), cyy + sz / 2 + 80 * k), names[1].upper(), font=nfnt, anchor="mm",
                       fill=mix(cols[1], 0.3), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            if a >= hit_at:
                b = a - hit_at
                if burst is not None and b < 0.5:
                    paste_center(img, burst, W / 2, cyy, W * (0.6 + 2.4 * b), max(0.0, 1 - b / 0.5), b * 200)
                pop = 1 + 0.6 * max(0.0, 1 - b / 0.12)
                f_ = render.font(int(vsf.size * pop))
                d.text((W / 2, cyy + 10 * k), "VS", font=f_, anchor="mm", fill=GOLD, stroke_width=int(10 * k),
                       stroke_fill=(0, 0, 0))
                d.text((W * 0.27, cyy + sz / 2 - 40 * k), names[0].upper(), font=nfnt, anchor="mm",
                       fill=mix(cols[0], 0.3), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                d.text((W * 0.73, cyy + sz / 2 + 80 * k), names[1].upper(), font=nfnt, anchor="mm",
                       fill=mix(cols[1], 0.3), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            d.text((W / 2, H * 0.12), "WHO WINS?", font=wf, anchor="mm", fill=(255, 255, 255),
                   stroke_width=int(7 * k), stroke_fill=(0, 0, 0))
            if a >= hit_at + 0.1:                                # pousse à commenter avant de regarder
                render.draw_rich(img, (W / 2, H * 0.74), "Comment your pick 👇", render.font(int(60 * k)),
                                 (255, 255, 255), "ma", int(5 * k), (0, 0, 0))
            if a >= hit_at + 0.2:                                # + demander like & follow
                render.like_follow(img, W / 2, H * 0.80, (a - hit_at - 0.2) / 0.3)
            if hit_at <= a < hit_at + 0.1:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(230 * (1 - (a - hit_at) / 0.1)))))
            if a > n / fps - 0.12:                               # flash de sortie → le combat
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (a - (n / fps - 0.12)) / 0.12))))
            proc.stdin.write(img.convert("RGB").tobytes())
        pauses.append((0.0, n / fps))
        intro_hit.append(hit_at)
        return n

    def finish_cut(x, y, lose) -> int:
        """« FINISH! » : arrêt sur image, zoom vers le dernier perso qui tombe, flash, écran qui craque, gros texte."""
        n = int(fps * 1.2)
        base = last_img.convert("RGBA")
        cr = fxengine.TexFX(seed + 7)
        cracks = [cr.tinted(t_, (255, 255, 255), 1.0) for t_ in ("scratch_01", "slash_01", "slash_03", "spark_05")]
        rr = random.Random(seed + 3)
        crack_pos = [(x + rr.uniform(-1, 1) * W * 0.35, y + rr.uniform(-1, 1) * W * 0.35, rr.uniform(0, 360),
                      rr.choice(cracks), rr.uniform(0.5, 1.0) * W) for _ in range(6)]
        ff = render.font(int(170 * k))
        burst_t = cr.tinted("star_09", mix(cols[1 - lose], 0.5) if lose >= 0 else (255, 240, 200), 1.0)
        cam2 = fxengine.Camera()
        winc = cols[1 - lose] if lose >= 0 else (255, 255, 255)
        label = "FINISH!" if lose >= 0 else "DRAW!"
        for f in range(n):
            a = f / fps
            z = 1 + 0.32 * (1 - (1 - min(1.0, a / 0.5)) ** 3)
            cw, ch = W / z, H / z
            x0 = min(max(0, x - cw / 2), W - cw)
            y0 = min(max(0, y - ch / 2), H - ch)
            img = base.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
            gray = img.convert("L").convert("RGBA")                  # le monde se fige (désaturé)
            img = Image.blend(img, gray, min(0.6, a * 3))
            if burst_t is not None and a < 0.7:                   # explosion sur le perso qui tombe
                paste_center(img, burst_t, (x - x0) * z, (y - y0) * z, W * (0.25 + 1.2 * a), max(0.0, 1 - a / 0.7),
                             a * 160)
            if a > 0.06:                                         # l'écran craque
                for cx_, cy_, rot, tx_, size in crack_pos:
                    if tx_ is not None:
                        paste_center(img, tx_, (cx_ - x0) * z, (cy_ - y0) * z, size, 0.9, rot)
            b = max(0.0, a - 0.1)
            pop = 1 + 1.4 * max(0.0, 1 - b / 0.14)
            f_ = render.font(max(20, int(ff.size * pop)))
            d = ImageDraw.Draw(img)
            sh = math.sin(a * 70) * 10 * k * max(0.0, 1 - b / 0.4)
            d.text((W / 2 + sh, H * 0.5), label, font=f_, anchor="mm", fill=GOLD if f % 4 < 2 or b > 0.3 else
                   (255, 255, 255), stroke_width=int(12 * k), stroke_fill=winc)
            if a < 0.08:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - a / 0.08)))))
            img = cam2.apply(img, a, 16 * k * max(0.0, 1 - a / 0.5), seed=f)
            if a < 0.15:
                img = fxengine.chroma(img, int(9 * k * (1 - a / 0.15)))
            proc.stdin.write(img.convert("RGB").tobytes())
        pauses.append((war.t, n / fps))
        finish_at.append((war.t, n / fps))
        return n

    auras: dict = {}
    anims: list = []                                             # animations 2D (images de library/_domain/fx/)
    parts = fxengine.Particles(seed)                             # étincelles, braises, débris (additif)
    tex = fxengine.TexFX(seed)                                   # particules texturées (Kenney Particle Pack, CC0)
    R_ = random.Random(seed + 99)

    def vdeg(dx, dy):
        """Rotation PIL (degrés) qui aligne une texture verticale sur la direction (dx, dy) de l'écran."""
        return -math.degrees(math.atan2(dy, dx)) - 90

    def vfx_boom(x, y, R, col, big=1.0):
        """Explosion : flash, boule de feu qui gonfle, onde de choc, étincelles, fumée et terre au sol."""
        hotc = mix(col, 0.35)
        tex.spawn("star_09", x, y, R * 1.0 * big, 0.2, (255, 250, 235), size1=R * 3.2 * big, hot=1.0)
        for j in range(5):
            tex.spawn(R_.choice(("fire_01", "fire_02")), x + R_.uniform(-R, R) * 0.3, y + R_.uniform(-R, R) * 0.3,
                      R * 0.7 * big, R_.uniform(0.5, 0.8), hotc, size1=R * R_.uniform(1.8, 2.6) * big,
                      spin=R_.uniform(-90, 90), hot=0.9, delay=j * 0.03)
        tex.spawn("circle_02", x, y, R * 0.4, 0.45, mix(col, 0.6), size1=R * 4.2 * big, hot=0.7, alpha=0.9)
        tex.spawn("circle_03", x, y, R * 0.3, 0.6, hotc, size1=R * 3.0 * big, hot=0.5, alpha=0.6, delay=0.06)
        for j in range(7):
            an = R_.uniform(0, 6.283)
            v = R_.uniform(500, 1100) * k
            tex.spawn(R_.choice(("spark_05", "spark_06", "trace_02")), x, y, cell * 1.0, R_.uniform(0.2, 0.35),
                      (255, 230, 170), vx=math.cos(an) * v, vy=math.sin(an) * v, rot=vdeg(math.cos(an), math.sin(an)),
                      stretch=3.0, hot=1.0, drag=3)
        for j in range(5):
            an = R_.uniform(0, 6.283)
            tex.spawn(R_.choice(("smoke_07", "smoke_08", "smoke_09", "smoke_10")), x, y, R * 0.8, R_.uniform(1.2, 1.8),
                      (58, 56, 64), size1=R * R_.uniform(2.0, 2.8) * big, vx=math.cos(an) * 60 * k,
                      vy=math.sin(an) * 60 * k - 30 * k, spin=R_.uniform(-30, 30), hot=0, glow=False, alpha=0.75,
                      delay=0.08)
        tex.spawn(R_.choice(("dirt_01", "dirt_02", "dirt_03")), x, y, R * 1.0, 1.1, (105, 92, 80), size1=R * 2.4 * big,
                  hot=0, glow=False, alpha=0.9)

    def vfx_hit(x, y, r, col):
        tex.spawn(R_.choice(("slash_01", "slash_02", "slash_03", "slash_04")), x, y, r * 4.2, 0.22, mix(col, 0.4),
                  size1=r * 5.2, hot=1.0)
        tex.spawn("star_08", x, y, r * 2.5, 0.2, (255, 245, 220), size1=r * 4.5, hot=1.0)

    def vfx_charge(x, y, col, size):
        """Concentration d'énergie avant un rayon : cercle qui se resserre + cœur qui brille."""
        tex.spawn("circle_03", x, y, size * 3.2, 0.35, mix(col, 0.5), size1=size * 0.6, hot=0.6, alpha=0.8)
        tex.spawn("magic_05", x, y, size * 0.8, 0.45, mix(col, 0.4), size1=size * 2.4, hot=1.0, spin=200)

    clones_seen: dict = {}
    subs_seen = [0]
    logs: list = []                                              # bûches de permutation au sol (t, x, y)
    log_img = _log_sprite(int(cell * 2.6))

    def poof(x, y, r):
        """Nuage de fumée des clones (« pouf ») : fumée blanche qui gonfle + petite étoile."""
        for _ in range(4):
            an = R_.uniform(0, 6.283)
            tex.spawn(R_.choice(("smoke_01", "smoke_02", "smoke_04")), x + math.cos(an) * r * 0.4,
                      y + math.sin(an) * r * 0.4, r * 1.6, 0.55, (235, 235, 240), size1=r * 3.2, glow=False, hot=0,
                      alpha=0.95, vx=math.cos(an) * 60 * k, vy=math.sin(an) * 60 * k, spin=R_.uniform(-60, 60))
        tex.spawn("star_06", x, y, r * 1.5, 0.2, (255, 255, 255), size1=r * 3, hot=1.0)

    def vfx_style(fx, st, age, c):
        """Effets propres au style de l'attaque (Chidori = éclairs, Rasengan = spirale, Amaterasu = flammes noires…)."""
        fam = fx["fam"]
        if fam in ("beam", "mega_beam") and age < 1.0:
            L = fx["length"] * min(1, age / fx["dur"])
            ca, sa = math.cos(fx["ang"]), math.sin(fx["ang"])
            x1, y1 = ox + fx["x"], oy + fx["y"]
            w = cell * (2 * fx["half"] + 1)
            hx, hy = x1 + ca * L, y1 + sa * L
            if st == "lightning":                                    # éclairs qui crépitent le long du rayon
                for _ in range(3):
                    q = R_.uniform(0.05, 1.0)
                    tex.spawn(R_.choice(("spark_01", "spark_02", "spark_03", "spark_04")), x1 + ca * L * q,
                              y1 + sa * L * q, w * R_.uniform(1.5, 2.6), 0.07, (200, 225, 255), hot=1.0,
                              rot=R_.uniform(0, 360))
                tex.spawn(R_.choice(("spark_05", "spark_06")), hx, hy, w * 1.2, 0.06, (225, 240, 255),
                          stretch=2.5, rot=R_.uniform(0, 360), hot=1.0)
            elif st == "spiral":                                     # sphère qui tourbillonne en tête
                tex.spawn(R_.choice(("twirl_01", "twirl_02", "twirl_03")), hx, hy, w * 2.6, 0.08, mix(c, 0.4),
                          rot=R_.uniform(0, 360), hot=0.9)
                tex.spawn("circle_05", hx, hy, w * 1.4, 0.06, (230, 245, 255), hot=1.0)
            elif st in ("blackfire", "fire"):
                fc = (20, 8, 30) if st == "blackfire" else (255, 120, 30)
                q = R_.uniform(0.1, 1.0)
                tex.spawn(R_.choice(("flame_01", "flame_02", "flame_03", "flame_04")), x1 + ca * L * q,
                          y1 + sa * L * q, w * 1.6, 0.35, fc, size1=w * 2.4, vy=-60 * k, glow=st == "fire",
                          hot=0 if st == "blackfire" else 0.8, alpha=0.9)
            elif st == "purple":                                     # Hollow Purple
                px, py = -sa, ca
                if age < 0.32:                                       # Bleu + Rouge qui se rejoignent → Violet
                    d = w * 2.6 * (1 - age / 0.32)
                    for col_, sg in (((60, 130, 255), 1), ((255, 50, 60), -1)):
                        tex.spawn("light_02", x1 + px * d * sg, y1 + py * d * sg, w * 1.8, 0.06, col_, hot=1.0)
                        tex.spawn("twirl_02", x1 + px * d * sg, y1 + py * d * sg, w * 1.6, 0.06, col_,
                                  rot=(age * 900 * sg) % 360, hot=0.8)
                elif age < 0.36:
                    tex.spawn("star_09", x1, y1, w * 2, 0.3, (230, 200, 255), size1=w * 7, hot=1.0)
                    ripples.append((war.t, x1, y1))
                big = 1.6 if fam == "mega_beam" else 1.0
                sr = max(w, cell * 4) * big                          # la sphère (violet, pas blanc)
                tex.spawn("light_03", hx, hy, sr * 4.0, 0.07, c, hot=0.2)
                tex.spawn("twirl_02", hx, hy, sr * 3.2, 0.07, c, rot=(age * 700) % 360, hot=0.3)
                tex.spawn("circle_05", hx, hy, sr * 2.2, 0.07, mix(c, 0.2), hot=0.35)
                tex.spawn("circle_05", hx, hy, sr * 1.1, 0.07, (14, 0, 26), glow=False, hot=0, alpha=0.95)
                for _ in range(2):                                   # l'espace est effacé derrière elle
                    q = R_.uniform(0.05, 1.0)
                    tex.spawn(R_.choice(("smoke_07", "smoke_08", "smoke_09")), x1 + ca * L * q, y1 + sa * L * q,
                              w * 1.4, 0.7, (40, 10, 70), size1=w * 2.2, glow=False, hot=0, alpha=0.7)
                    tex.spawn("spark_07", hx + R_.uniform(-1, 1) * w, hy + R_.uniform(-1, 1) * w, w * 0.8, 0.12,
                              (220, 180, 255), rot=R_.uniform(0, 360), hot=1.0)
                if fam == "mega_beam" and int(age * 6) != int((age - 1 / fps) * 6):
                    ripples.append((war.t, hx, hy))                  # l'espace se déforme sur son passage
            elif st == "blue":                                       # Lapse Blue : tout est aspiré vers la sphère
                sr = max(w, cell * 3.5)
                tex.spawn("light_03", hx, hy, sr * 4.2, 0.06, c, hot=0.25)
                tex.spawn("twirl_01", hx, hy, sr * 3.4, 0.06, c, rot=(-age * 1100) % 360, hot=0.4)
                tex.spawn("twirl_03", hx, hy, sr * 2.4, 0.06, mix(c, 0.3), rot=(-age * 1500) % 360, hot=0.5)
                tex.spawn("circle_05", hx, hy, sr * 1.2, 0.06, (200, 225, 255), hot=0.8)
                for _ in range(3):
                    an = R_.uniform(0, 6.283)
                    rr_ = sr * R_.uniform(2.0, 4.0)
                    tex.spawn(R_.choice(("trace_01", "spark_03", "light_01")), hx + math.cos(an) * rr_,
                              hy + math.sin(an) * rr_, w * 0.6, 0.2, (150, 200, 255), vx=-math.cos(an) * rr_ * 5,
                              vy=-math.sin(an) * rr_ * 5, rot=math.degrees(an), stretch=3.0, hot=1.0)
        elif fam in ("domain", "shrine") and st == "void" and age < 1.4:   # Unlimited Void : l'infini étoilé
            b = fx["ball"]
            x, y = ox + b["x"], oy + b["y"]
            R = fx["radius"] * min(1, age / fx["dur"])
            if age < 1 / fps + 1e-6:
                tex.spawn("circle_05", x, y, fx["radius"] * 0.3, 1.4, (8, 4, 22), size1=fx["radius"] * 2.6, glow=False,
                          hot=0, alpha=0.85)
                tex.spawn("star_09", x, y, cell * 3, 0.4, (235, 245, 255), size1=fx["radius"] * 2.2, hot=1.0)
                ripples.append((war.t, x, y))
            for _ in range(5):
                an, rr_ = R_.uniform(0, 6.283), R * math.sqrt(R_.random())
                tex.spawn(R_.choice(("star_01", "star_04", "star_05", "light_01")), x + math.cos(an) * rr_,
                          y + math.sin(an) * rr_, cell * R_.uniform(0.6, 1.6), R_.uniform(0.3, 0.8),
                          R_.choice(((255, 255, 255), (170, 220, 255), (200, 170, 255))), hot=1.0,
                          rot=R_.uniform(0, 360))
            tex.spawn("magic_02", x, y, R * 1.9, 0.06, (150, 200, 255), rot=(age * 60) % 360, hot=0.6, alpha=0.6)
        elif fam == "shots" and st == "red":                         # Reversal Red : chaque impact repousse tout
            b = fx["ball"]
            for i, (tx, ty) in enumerate(fx["shots"]):
                a = (age - i * 0.05) / 0.3
                if 1 <= a < 1 + 1.5 / (0.3 * fps):
                    tex.spawn("circle_02", ox + tx, oy + ty, cell * 1.0, 0.32, c, size1=cell * 7, hot=1.0)
                    tex.spawn("star_08", ox + tx, oy + ty, cell * 2, 0.15, (255, 230, 230), size1=cell * 4, hot=1.0)
        elif fam == "bomb" and age < fx.get("delay", 0):
            a = age / max(1e-3, fx["delay"])
            x, y = ox + fx["tx"], oy + fx["ty"] * a * a
            if st == "lightning":                                    # Kirin : la foudre tombe du ciel
                ty = oy + fx["ty"]
                tex.spawn(R_.choice(("spark_05", "spark_06")), x + R_.uniform(-1, 1) * cell, (oy - 20 * k + ty) / 2,
                          cell * 4, 0.06, (215, 235, 255), stretch=max(1.0, (ty - oy) / (cell * 4)), rot=0, hot=1.0)
                tex.spawn("light_03", x, ty, cell * (4 + 6 * a), 0.06, (180, 210, 255), hot=1.0)
            elif st == "spiral":                                     # Rasenshuriken : disque qui tourne
                for j in range(4):
                    tex.spawn("slash_04", x, y, fx["radius"] * 1.3, 0.05, (220, 240, 255),
                              rot=(age * 1400 + j * 90) % 360, hot=1.0, alpha=0.9)
                tex.spawn("twirl_01", x, y, fx["radius"] * 0.8, 0.05, mix(c, 0.4), rot=age * 900 % 360, hot=1.0)
        elif fam == "shots" and st in ("blackfire", "fire", "lightning"):
            b = fx["ball"]
            for i, (tx, ty) in enumerate(fx["shots"]):
                a = (age - i * 0.05) / 0.3
                if 0 <= a < 1:
                    x = ox + b["x"] + (tx - b["x"]) * a
                    y = oy + b["y"] + (ty - b["y"]) * a
                    if st == "lightning":
                        tex.spawn(R_.choice(("spark_01", "spark_03")), x, y, cell * 2.2, 0.06, (210, 230, 255),
                                  rot=R_.uniform(0, 360), hot=1.0)
                    else:
                        tex.spawn(R_.choice(("flame_05", "flame_06")), x, y, cell * 1.8, 0.25,
                                  (25, 10, 35) if st == "blackfire" else (255, 130, 40), size1=cell * 2.4,
                                  vy=-80 * k, glow=st == "fire", hot=0 if st == "blackfire" else 0.8)
                elif 1 <= a < 1.06 and st == "blackfire":            # les flammes noires restent au sol
                    if (id(fx), i) not in burn_keys:                     # Amaterasu : brûle ~11 s sur le terrain
                        burn_keys.add((id(fx), i))
                        burns.append((war.t, ox + tx, oy + ty, R_.random()))
                    for _ in range(3):
                        tex.spawn(R_.choice(("flame_01", "flame_02", "flame_05")), ox + tx + R_.uniform(-1, 1) * cell,
                                  oy + ty + R_.uniform(-1, 1) * cell, cell * 2.2, 1.4, (18, 6, 26), size1=cell * 3,
                                  vy=-30 * k, glow=False, hot=0, alpha=0.95)
                    tex.spawn("circle_05", ox + tx, oy + ty, cell * 2.5, 0.6, (140, 60, 200), hot=0.3, alpha=0.6)

    def vfx_frame():
        """Effets continus, à chaque image : rayons (traînées qui filent, tête qui brûle, flamme au départ),
        projectiles (traînée), Beam Clash (contact), auras en flammes (transformé / Sparking)."""
        present = set()
        for b in war.balls:                                           # clones : « pouf » en apparaissant / partant
            if b["kind"] == "clone":
                present.add(b["id"])
                clones_seen[b["id"]] = (ox + b["x"], oy + b["y"], b["r"])
                if b.get("_poofed") is None:
                    b["_poofed"] = True
                    poof(ox + b["x"], oy + b["y"], b["r"])
        for cid in [c_ for c_ in clones_seen if c_ not in present]:
            poof(*clones_seen.pop(cid))
        for sub in war.subs[subs_seen[0]:]:                         # permutation : pouf + bûche + pouf à l'arrivée
            t0, x0, y0, tm, x1, y1 = sub
            poof(ox + x0, oy + y0, cell * 1.6)
            poof(ox + x1, oy + y1, cell * 1.2)
            logs.append((t0, ox + x0, oy + y0))
            banners.append({"t0": t0, "team": tm, "who": names[tm], "move": "Substitution Jutsu", "big": False})
        subs_seen[0] = len(war.subs)
        for fx in war.fx:
            age = war.t - fx["t0"]
            c = mix(cols[fx["team"]], 0.25)
            st = style_of(fx.get("name"))
            c = STYLE_COL.get(st, c)
            if st:
                vfx_style(fx, st, age, c)
            if fx["fam"] in ("beam", "mega_beam") and age < 1.0:
                L = fx["length"] * min(1, age / fx["dur"])
                ca, sa = math.cos(fx["ang"]), math.sin(fx["ang"])
                x1, y1 = ox + fx["x"], oy + fx["y"]
                w = cell * (2 * fx["half"] + 1)
                if age < 0.02:
                    vfx_charge(x1, y1, c, w)
                hx, hy = x1 + ca * L, y1 + sa * L
                tex.spawn("light_03", hx, hy, w * 2.6, 0.08, c, hot=1.0, rot=R_.uniform(0, 360))
                tex.spawn("star_09", hx, hy, w * 1.8, 0.08, (255, 255, 240), hot=1.0, rot=R_.uniform(0, 360))
                if int(war.t * fps) % 2 == 0:
                    tex.spawn(R_.choice(("muzzle_02", "muzzle_04", "muzzle_05")), x1 + ca * w * 0.6, y1 + sa * w * 0.6,
                              w * 1.6, 0.12, c, stretch=1.6, rot=vdeg(ca, sa) + 180, hot=0.9)
                for _ in range(2):                                    # traînées d'énergie qui filent dans le rayon
                    q = R_.uniform(0.05, 0.95)
                    off = R_.uniform(-0.35, 0.35) * w
                    tex.spawn(R_.choice(("trace_01", "trace_03", "trace_06")), x1 + ca * L * q - sa * off,
                              y1 + sa * L * q + ca * off, w * 0.5, 0.18, (255, 255, 255), vx=ca * 1400 * k,
                              vy=sa * 1400 * k, rot=vdeg(ca, sa), stretch=5.0, hot=1.0, alpha=0.8)
            elif fx["fam"] == "shots":
                b = fx["ball"]
                for i, (tx, ty) in enumerate(fx["shots"]):
                    a = (age - i * 0.05) / 0.3
                    if 0 <= a < 1:
                        x = ox + b["x"] + (tx - b["x"]) * a
                        y = oy + b["y"] + (ty - b["y"]) * a
                        dx, dy = tx - b["x"], ty - b["y"]
                        tex.spawn("trace_05", x, y, cell * 0.9, 0.12, c, rot=vdeg(dx, dy), stretch=3.5, hot=1.0)
                        tex.spawn("light_02", x, y, cell * 1.6, 0.06, c, hot=1.0)
                    elif 1 <= a < 1.12:
                        tex.spawn("star_08", ox + tx, oy + ty, cell * 1.5, 0.2, (255, 240, 210), size1=cell * 3.2,
                                  hot=1.0)
        bc_ = war.beam
        if bc_ and war.t - bc_["t0"] > 0.3:
            x, y = ox + bc_["pos"] * gw, oy + bc_["y"]
            tex.spawn("star_09", x, y, cell * 7, 0.08, (255, 250, 220), hot=1.0, rot=R_.uniform(0, 360))
            tex.spawn(R_.choice(("spark_01", "spark_02", "spark_03", "spark_04")), x + R_.uniform(-1, 1) * cell * 2,
                      y + R_.uniform(-1, 1) * cell * 2, cell * 5, 0.12, (255, 230, 160), hot=1.0)
        if int(war.t * fps) % 2 == 0:
            for b in war.mains(0) + war.mains(1):                       # auras en flammes
                tm = b["team"]
                if war.transformed[tm] is not None:
                    ac = hex_rgb(sheets[tm].get("aura"), mix(cols[tm], 0.4))
                elif war.t < war.sparking[tm]:
                    ac = GOLD
                else:
                    continue
                tex.spawn(R_.choice(("flame_05", "flame_06", "muzzle_01", "muzzle_03")),
                          ox + b["x"] + R_.uniform(-0.6, 0.6) * b["r"], oy + b["y"] - b["r"] * 0.4,
                          b["r"] * 1.4, 0.35, ac, size1=b["r"] * 1.9, vy=-140 * k, rot=R_.uniform(-12, 12), hot=0.7,
                          alpha=0.85)

    cam = fxengine.Camera()                                      # zoom « punch » + tremblement
    vig = fxengine.vignette(W, H, 0.45)
    hit = {"stop": 0, "chroma": -9.0}                            # arrêt sur impact (images figées), aberration
    ripples: list = []                                           # ondes de choc (déformation de l'image)
    post_fx = [-9.0]                                             # instant de retour d'une cinématique
    flips: dict = {}
    ROCK = (96, 88, 84)
    decals: list = []                                            # traces au sol (cratères, brûlures) qui s'effacent
    leapers: list = []                                           # Kage Bunshin : vague de clones qui bondissent
    leap_land: list = []
    LEAP = 0.42
    burns: list = []                                             # flammes noires d'Amaterasu qui restent (11 s)
    burn_keys: set = set()
    BURN_S = 11.0
    scorch = _scorch_sprite()
    tiles: dict = {}

    def tile(team, var, fl):
        """Case texturée : relief (clair en haut à gauche, sombre en bas à droite), grain, éclair blanc si prise."""
        key = (team, var, fl)
        if key not in tiles:
            import numpy as np
            c = np.array(cols[team], dtype=np.float32)
            n = max(2, int(cell) - 2)
            yy, xx = np.mgrid[0:n, 0:n] / max(1, n - 1)
            shade = 1.12 - 0.3 * (xx + yy) / 2                      # lumière en haut à gauche
            rng = np.random.default_rng(var * 7 + team)
            grain = rng.normal(0, 0.035, (n, n))
            edge = np.minimum.reduce([xx, yy, 1 - xx, 1 - yy])        # biseau
            bevel = np.where(edge < 0.12, np.where(xx + yy < 1, 1.18, 0.78), 1.0)
            rgb = c[None, None, :] * (shade * bevel + grain)[..., None]
            rgb = rgb + (255 - rgb) * (fl / 4) * 0.65
            tiles[key] = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
        return tiles[key]

    def crater(x, y, R):
        decals.append((war.t, x, y, R, random.uniform(0, 6.28)))

    def rubble(x, y, n, spread=(200, 700)):
        """Éclats de roche + bouffées de poussière."""
        for _ in range(int(n)):
            g = random.uniform(-25, 30)
            parts.emit(x, y, 1, speed=tuple(v * k for v in spread), col=(ROCK[0] + g, ROCK[1] + g, ROCK[2] + g),
                       life=(0.7, 1.4), size=(3 * k, 7 * k), kind=fxengine.DEBRIS)
        parts.emit(x, y, max(3, int(n / 3)), speed=(40 * k, 160 * k), col=(150, 148, 155), life=(0.8, 1.6),
                   size=(10 * k, 22 * k), kind=fxengine.SMOKE)

    def flip(name):
        """Animation image par image : fx/<nom>.gif|.webp animé, ou dossier fx/<nom>/ d'images (sauf formes)."""
        if name not in flips:
            fr = []
            base = library.root() / "_domain" / "fx"
            sheet = next((p for p in base.glob(f"{name}_sheet*") if p.suffix.lower() in (".png", ".webp")), None) \
                if base.is_dir() else None
            if sheet is not None:                                # planche Effekseer : « Kamehameha_sheet_8.png »
                m = re.search(r"_sheet_?(\d+)", sheet.stem)
                im = Image.open(sheet).convert("RGBA")
                ncol = int(m.group(1)) if m else max(1, round(im.width / im.height))
                fw = im.width // ncol
                nrow = max(1, im.height // fw)
                fr = [_prep_sprite(im.crop((c * fw, r_ * fw, (c + 1) * fw, (r_ + 1) * fw)), crop=False)
                      for r_ in range(nrow) for c in range(ncol)]
                fr = _union_crop([f for f in fr if f.getchannel("A").getbbox()])
                if len(fr) > 1:
                    flips[name] = fr
                    return fr
            for cand in (base / f"{name}.gif", base / f"{name}.webp", base / f"{name}_frames",
                         base / f"{name}.mp4", base / f"{name}.webm", base / f"{name}.mov"):   # vidéo (IA, Effekseer…)
                if cand.exists():
                    fr = _union_crop([_prep_sprite(f, crop=False) for f in fxengine.flipbook(cand)])
                    if len(fr) > 1:
                        break
                    fr = []
            flips[name] = fr
        return flips[name]

    def emit(kind, x, y, n, col, speed=(250, 700), life=(0.25, 0.6), size=(2, 4.5), **kw):
        parts.emit(x, y, n, speed=tuple(v * k for v in speed), col=col, life=life,
                   size=tuple(v * k for v in size), kind=kind, **kw)
    seen_fx: set = set()
    last_hurt: dict = {}
    seen_ko = [0]
    tinted: dict = {}

    def ui(team) -> str | None:
        """Dossier d'effets de la forme secrète si le camp est transformé (ex. fx/Ultra Instinct/)."""
        return fdir[team] if team is not None and war.transformed[team] is not None else None

    def gfx(name: str, col=None, team=None):
        """Image d'effet (impact, burst, ring, ghost, slash_1…) : celle de la forme secrète si le camp est transformé
        (fx/<Secret>/<nom>.png, telle quelle), sinon la générique teintée à la couleur du camp."""
        sub = ui(team)
        key = (name, col, sub)
        if key not in tinted:
            spr = fx_sprite(name, sub=sub) if sub else None
            if spr is None:
                spr = fx_sprite(name)
                if spr is not None and col is not None:
                    spr = hue_tint(spr, col)
            tinted[key] = spr
        return tinted[key]

    def atk(fx_name, team, slot):
        """Image d'une attaque ; transformé : version de la forme (fx/<Secret>/<Attaque>.png) sinon recolorée
        à la couleur de l'aura (`aura:` de la fiche) → toutes ses attaques changent."""
        key = ("atk", fx_name, team, war.transformed[team] is not None)
        if key not in tinted:
            fr = flip(fx_name) if fx_name else []                # animation image par image (Effekseer, GIF…)
            spr = list(fr) if fr else fx_sprite(fx_name, names[team], slot)
            if spr is None and PACK and slot in ("zone", "shots", "secret") and ui(team) is None:
                fam_ = (sheets[team].get(slot) or {}).get("fam", "")
                c_ = hex_rgb(sheets[team].get("aura"), cols[team]) if war.transformed[team] is not None else cols[team]
                c_ = STYLE_COL.get(style_of(fx_name), c_)
                if fam_ == "shots":
                    spr = packfx("energy_disc" if style_of(fx_name) == "spiral" else "ki_blast", mix(c_, 0.3))
                elif fam_ in ("bomb", "meteor"):
                    spr = packfx("energy_ball", mix(c_, 0.3))
                spr = spr or None
            if spr is None and PROC and slot in ("front", "zone", "shots", "secret"):   # rien de fourni → généré
                fam_ = (sheets[team].get(slot) or {}).get("fam", "")
                kind = "beam" if fam_ in ("beam", "mega_beam") else ("orb" if fam_ in ("bomb", "meteor", "shots") else None)
                if kind == "beam" and PACK and ui(team) is None:
                    kind = None                                  # le rayon du pack (pack_beam) passe avant
                if kind:
                    c_ = hex_rgb(sheets[team].get("aura"), cols[team]) if war.transformed[team] is not None else cols[team]
                    spr = procfx(kind, mix(STYLE_COL.get(style_of(fx_name), c_), 0.3))
            if war.transformed[team] is not None:
                own = fx_sprite(fx_name, sub=fdir[team]) if fdir[team] else None
                if own is not None:
                    spr = own
                elif spr is not None and fdir[team] and sheets[team].get("aura"):   # seulement si la forme a son
                    col_ = hex_rgb(sheets[team].get("aura"), cols[team])
                    spr = [hue_tint(f, col_) for f in spr] if isinstance(spr, list) else hue_tint(spr, col_)
            tinted[key] = spr
        return tinted[key]

    def atk_at(fx_name, team, slot, age):
        """L'image de l'attaque à cet instant (flipbook : 24 images/s, en boucle)."""
        spr = atk(fx_name, team, slot)
        if isinstance(spr, list):
            return spr[int(age * 24) % len(spr)] if spr else None
        return spr

    PROC = bool(config.get()["slides"].get("domain", {}).get("procedural_vfx", True))
    PACK = bool(config.get()["slides"].get("domain", {}).get("vfx_pack", True)) and vfxpack.available()
    PACKMAP = {"burst": "explosion_dome", "explosion": "explosion_dome", "impact": "punch_impact",
               "blast_hit": "ki_blast_hit", "flash": "solar_flash", "charge": "beam_charge",
               "teleport_back": ("teleport", "back"), "teleport_front": ("teleport", "front"),
               "afterimage": "afterimage", "kiai": "kiai_wave", "aura_burst": "aura_burst"}
    packs: dict = {}

    def packfx(eid, col, layer=None):
        """Images du pack pixel-art teintées (cache par couleur)."""
        key = (eid, layer, tuple(int(c) // 8 for c in col[:3]))
        if key not in packs:
            packs[key] = list(vfxpack.frames(eid, layer, tuple(col[:3])))
        return packs[key]
    PROCMAP = {"burst": "explosion", "ring": "ring", "impact": "hit", "sparks": "lightning", "slash_1": "slash",
               "slash_2": "slash", "slash_3": "slash", "explosion": "explosion"}
    procs: dict = {}

    def pack_beam(team, L, th, age, name=None):
        """Rayon du pack (queue + corps répété + tête) à la bonne longueur, teinté ; None sans pack."""
        if not PACK or ui(team) is not None:
            return None
        c_ = hex_rgb(sheets[team].get("aura"), cols[team]) if war.transformed[team] is not None else cols[team]
        c_ = STYLE_COL.get(style_of(name), c_)                   # Hollow Purple = violet, quel que soit le camp
        spiral = style_of(name) == "spiral"
        H = 128 if spiral else 192
        cells = int(max(1, min(60, (L / max(1.0, th) * H - (96 if spiral else 352)) / 128)))
        fr_ = int(age * vfxpack.fps())
        return vfxpack.beam_strip(cells, fr_, tuple(int(c) for c in mix(c_, 0.15)[:3]), spiral)

    def procfx(kind, col):
        """Animation procédurale (vfxgen) colorisée, en cache par couleur."""
        key = (kind, tuple(int(c) // 8 for c in col[:3]))
        if key not in procs:
            procs[key] = list(vfxgen.frames(kind, 256, tuple(col[:3])))
        return procs[key]

    def anim(name, x, y, s0, s1, dur, col=None, alpha=1.0, rot=None, spin=0.0, delay=0.0, team=None):
        """Ordre : image/flipbook fourni par l'utilisateur > pack pixel-art acheté > animation générée > image fixe."""
        fr = flip(name)
        ax = ay = 0.5
        c_ = col if col is not None else (mix(cols[team], 0.35) if team is not None else (255, 225, 140))
        if not fr and PACK and name in PACKMAP and ui(team) is None:
            eid = PACKMAP[name]
            eid, layer = (eid if isinstance(eid, tuple) else (eid, None))
            fr = packfx(eid, c_, layer)
            if fr:
                ax, ay = vfxpack.anchor(eid)
        if not fr and PROC and name in PROCMAP and ui(team) is None:   # pas d'image fournie : animation générée
            fr = procfx(PROCMAP[name], c_)
        spr = fr[0] if fr else gfx(name, col, team)
        if spr is not None:
            anims.append({"spr": spr, "frames": fr, "t0": war.t + delay, "x": x, "y": y, "s0": s0, "s1": s1,
                          "dur": dur, "al": alpha, "rot": random.uniform(0, 6.28) if rot is None else rot,
                          "spin": spin, "ax": ax, "ay": ay})

    def spawn_anims():
        """Déclenche les animations : impact quand un perso est touché, explosion des bombes, onde des domaines,
        entailles du Shrine, image rémanente + anneau du Vanish, explosion au K.O., étincelles du Beam Clash."""
        for fx in war.fx:
            fam, c, age = fx["fam"], mix(cols[fx["team"]], 0.2), war.t - fx["t0"]
            key = id(fx)
            if PACK and ui(fx["team"]) is None:
                if fam == "shots" and fx.get("ball") is not None:          # projectile qui arrive : petit impact
                    b_ = fx["ball"]
                    for i_, (tx_, ty_) in enumerate(fx["shots"]):
                        if (age - i_ * 0.05) / 0.3 >= 1 and (key, "sh", i_) not in seen_fx:
                            seen_fx.add((key, "sh", i_))
                            anim("blast_hit", ox + tx_, oy + ty_, cell * 2.2, cell * 3.2, 0.3, mix(cols[fx["team"]], 0.4),
                                 team=fx["team"])
                if fam in ("beam", "mega_beam") and (key, "ch") not in seen_fx:   # charge au départ du rayon
                    seen_fx.add((key, "ch"))
                    anim("charge", ox + fx["x"], oy + fx["y"], cell * 3, cell * 3.4, 1.0, mix(cols[fx["team"]], 0.4),
                         team=fx["team"])
                if fam == "vanish" and (key, "tp") not in seen_fx:               # téléportation : départ + arrivée
                    seen_fx.add((key, "tp"))
                    rb_ = fx["ball"]["r"]
                    for (px_, py_), dl in (((fx["x0"], fx["y0"]), 0.0), ((fx["x"], fx["y"]), 0.12)):
                        anim("teleport_back", ox + px_, oy + py_ + rb_, rb_ * 5, rb_ * 5.5, 0.6,
                             mix(cols[fx["team"]], 0.4), team=fx["team"], delay=dl)
                        anim("teleport_front", ox + px_, oy + py_ + rb_, rb_ * 5, rb_ * 5.5, 0.6,
                             mix(cols[fx["team"]], 0.4), team=fx["team"], delay=dl)
            if fam == "bomb" and age >= fx.get("delay", 0) and (key, "boom") not in seen_fx:
                seen_fx.add((key, "boom"))
                x, y = ox + fx["tx"], oy + fx["ty"]
                tm = fx["team"]
                ripples.append((war.t, x, y))
                anim("burst", x, y, fx["radius"] * 0.6, fx["radius"] * 2.6, 0.55, c, spin=1.5, team=tm)
                anim("ring", x, y, fx["radius"] * 0.5, fx["radius"] * 3.0, 0.5, c, team=tm)
                anim("impact", x, y, fx["radius"] * 1.5, fx["radius"] * 3.4, 0.35, None, team=tm)
                anim("explosion", x, y, fx["radius"] * 2, fx["radius"] * 3, 0.6, None)    # flipbook si fourni
                emit(fxengine.SPARK, x, y, 55, mix(c, 0.5), speed=(300, 900))
                emit(fxengine.EMBER, x, y, 25, c, speed=(80, 300), life=(0.5, 1.1), size=(2, 5))
                rubble(x, y, 22)
                crater(x, y, fx["radius"] * 0.9)
                vfx_boom(x, y, fx["radius"] * 0.6, cols[tm])
                cam.punch(war.t, x, y, 0.045, 0.35)
            elif fam in ("domain", "shrine") and (key, "wave") not in seen_fx:
                seen_fx.add((key, "wave"))
                b = fx["ball"]
                anim("ring", ox + b["x"], oy + b["y"], cell * 2, fx["radius"] * 2.6, 0.9, c, team=fx["team"])
                tex.spawn(R_.choice(("magic_01", "magic_02")), ox + b["x"], oy + b["y"], fx["radius"] * 0.6, 1.6,
                          mix(c, 0.3), size1=fx["radius"] * 2.4, spin=40, hot=0.8, fade_in=0.2)
                tex.spawn("magic_03", ox + b["x"], oy + b["y"], cell * 4, 0.9, mix(c, 0.5), size1=cell * 9,
                          spin=-90, hot=1.0)
                anim("burst", ox + b["x"], oy + b["y"], cell * 2, fx["radius"] * 1.8, 0.6, c, alpha=0.8,
                     team=fx["team"])
            if fam == "shrine" and age < fx["dur"] + 0.8 and fx_sprite("slash_1") is not None:
                b = fx["ball"]
                rr = random.Random(int(war.t * 1000))
                if rr.random() < 0.7:                                   # entailles nettes (Kenney) en plus
                    R2 = fx["radius"] * min(1, age / max(0.05, fx["dur"]))
                    tex.spawn(rr.choice(("slash_01", "slash_02", "slash_03", "slash_04", "scratch_01")),
                              ox + b["x"] + rr.uniform(-R2, R2) * 0.8, oy + b["y"] + rr.uniform(-R2, R2) * 0.8,
                              cell * 3.5, 0.22, mix(c, 0.5), rot=rr.uniform(0, 360), hot=1.0)
                if rr.random() < 0.55:                                  # entailles qui apparaissent partout
                    R = fx["radius"] * min(1, age / max(0.05, fx["dur"]))
                    anim(rr.choice(("slash_1", "slash_2", "slash_3")), ox + b["x"] + rr.uniform(-R, R) * 0.8,
                         oy + b["y"] + rr.uniform(-R, R) * 0.8, cell * 3, cell * 4.5, 0.28, None,
                         rot=rr.uniform(0, 6.28))
            if fam == "vanish" and (key, "v") not in seen_fx:
                seen_fx.add((key, "v"))
                rb = fx["ball"]["r"]
                anim("ghost", ox + fx["x0"], oy + fx["y0"], rb * 4, rb * 4.4, 0.45, mix(cols[fx["team"]], 0.4),
                     alpha=0.8, rot=0, team=fx["team"])
                anim("streak", (ox + fx["x0"] + ox + fx["x"]) / 2, (oy + fx["y0"] + oy + fx["y"]) / 2, rb * 5, rb * 6,
                     0.3, c, rot=math.atan2(fx["y"] - fx["y0"], fx["x"] - fx["x0"]) + math.pi / 2, team=fx["team"])
                anim("ring", ox + fx["x"], oy + fx["y"], rb * 1.5, fx["radius"] * 2.2, 0.35, c, team=fx["team"])
                anim("impact", ox + fx["x"], oy + fx["y"], rb * 3, rb * 6, 0.25, None, team=fx["team"])
                tex.spawn(R_.choice(("twirl_01", "twirl_02", "twirl_03")), ox + fx["x0"], oy + fx["y0"], rb * 3, 0.35,
                          mix(c, 0.4), size1=rb * 5, spin=-500, hot=0.9)
                tex.spawn("star_07", ox + fx["x"], oy + fx["y"], rb * 2, 0.25, (255, 255, 255), size1=rb * 5, hot=1.0)
                emit(fxengine.SPARK, ox + fx["x"], oy + fx["y"], 22, mix(c, 0.6), speed=(400, 1000), life=(0.15, 0.35))
            if ui(fx["team"]) and fam not in ("vanish", "regen") and (key, "ui") not in seen_fx:
                seen_fx.add((key, "ui"))                               # forme secrète : chaque attaque scintille
                tm = fx["team"]
                if fam in ("beam", "mega_beam"):
                    pts = [(ox + fx["x"] + math.cos(fx["ang"]) * fx["length"] * q,
                            oy + fx["y"] + math.sin(fx["ang"]) * fx["length"] * q) for q in (0.35, 0.7, 1.0)]
                elif fam == "shots":
                    pts = [(ox + tx, oy + ty) for tx, ty in fx["shots"][::2]]
                elif fam == "bomb":
                    pts = [(ox + fx["tx"], oy + fx["ty"])]
                elif fx.get("ball") is not None:
                    pts = [(ox + fx["ball"]["x"], oy + fx["ball"]["y"])]
                else:
                    pts = []
                for j, (px_, py_) in enumerate(pts):
                    anim("sparks", px_, py_, cell * 3, cell * 6, 0.5, None, team=tm, delay=0.12 * j, spin=1.0)
                    anim("burst", px_, py_, cell * 2, cell * 7, 0.35, None, alpha=0.8, team=tm, delay=0.12 * j)
        for b in war.balls:                                             # touché → impact
            if b["kind"] == "main" and b["hurt"] > last_hurt.get(b["id"], -9.0):
                last_hurt[b["id"]] = b["hurt"]
                anim("impact", ox + b["x"], oy + b["y"], b["r"] * 3, b["r"] * 7, 0.3, None, team=1 - b["team"])
                anim("sparks", ox + b["x"], oy + b["y"], b["r"] * 3, b["r"] * 5, 0.4, mix(cols[1 - b["team"]], 0.2),
                     team=1 - b["team"])
                emit(fxengine.SPARK, ox + b["x"], oy + b["y"], 28, (255, 235, 180), speed=(350, 950))
                cam.punch(war.t, ox + b["x"], oy + b["y"], 0.025, 0.25)
                rubble(ox + b["x"], oy + b["y"], 7, (150, 450))
                vfx_hit(ox + b["x"], oy + b["y"], b["r"], cols[1 - b["team"]])
        for t0, team, kx, ky in director.kos[seen_ko[0]:]:              # K.O. → grosse explosion
            anim("burst", ox + kx, oy + ky, cell * 2, cell * 12, 0.7, mix(cols[1 - team], 0.2), spin=2, team=1 - team)
            anim("ring", ox + kx, oy + ky, cell * 2, cell * 14, 0.6, mix(cols[1 - team], 0.2), team=1 - team)
            emit(fxengine.SPARK, ox + kx, oy + ky, 90, (255, 240, 200), speed=(400, 1300), life=(0.3, 0.7))
            emit(fxengine.EMBER, ox + kx, oy + ky, 40, mix(cols[1 - team], 0.3), speed=(100, 400), life=(0.6, 1.3),
                 size=(2, 6))
            cam.punch(war.t, ox + kx, oy + ky, 0.07, 0.45)
            if PACK:
                anim("flash", ox + kx, oy + ky, cell * 6, cell * 14, 0.7, (255, 245, 210), team=1 - team)
            rubble(ox + kx, oy + ky, 30, (300, 900))
            vfx_boom(ox + kx, oy + ky, cell * 4, cols[1 - team], 1.3)
            crater(ox + kx, oy + ky, cell * 5)
            hit["stop"] = max(hit["stop"], 4)
            hit["chroma"] = war.t
            hit["col"] = mix(cols[1 - team], 0.5)
            ripples.append((war.t, ox + kx, oy + ky))
        seen_ko[0] = len(director.kos)
        bc_ = war.beam
        if bc_ and war.t - bc_["t0"] > 0.35:                            # Beam Clash : étincelles au contact
            if int(war.t * fps) % 3 == 0:
                anim("impact", ox + bc_["pos"] * gw, oy + bc_["y"], cell * 6, cell * 11, 0.2, (255, 214, 10))
            emit(fxengine.SPARK, ox + bc_["pos"] * gw, oy + bc_["y"], 9, (255, 230, 140), speed=(500, 1400),
                 life=(0.12, 0.35))
            if (war.t - bc_["t0"]) / bc_["dur"] > 0.97 and not hit.get("clash_end"):
                hit["clash_end"] = True                                  # le rayon gagnant passe : gros impact
                hit["stop"] = max(hit["stop"], 6)
                hit["chroma"] = war.t
                hit["col"] = (255, 240, 200)
                ripples.append((war.t, ox + bc_["pos"] * gw, oy + bc_["y"]))
                cam.punch(war.t, ox + (gw if bc_["winner"] == 0 else 0), oy + bc_["y"], 0.08, 0.5)
                ex_ = ox + (gw if bc_["winner"] == 0 else 0)
                rubble(ex_, oy + bc_["y"], 45, (300, 1100))
                vfx_boom(ex_, oy + bc_["y"], cell * 5, cols[bc_["winner"]], 1.5)
                crater(ex_, oy + bc_["y"], cell * 7)
        for fx in war.fx:                                               # tête des rayons : gerbe d'étincelles
            if fx["fam"] in ("beam", "mega_beam") and war.t - fx["t0"] < fx["dur"] + 0.1:
                L = fx["length"] * min(1, (war.t - fx["t0"]) / fx["dur"])
                emit(fxengine.SPARK, ox + fx["x"] + math.cos(fx["ang"]) * L, oy + fx["y"] + math.sin(fx["ang"]) * L,
                     4, mix(cols[fx["team"]], 0.5), speed=(200, 700), life=(0.1, 0.3))
        for b in war.mains(0) + war.mains(1):                           # braises : transformé / Sparking
            tm = b["team"]
            if war.transformed[tm] is not None:
                emit(fxengine.EMBER, ox + b["x"] + random.uniform(-b["r"], b["r"]), oy + b["y"] + b["r"] * 0.5, 1,
                     hex_rgb(sheets[tm].get("aura"), mix(cols[tm], 0.4)), speed=(40, 120), life=(0.4, 0.9),
                     size=(1.5, 3.5), angle=-math.pi / 2, spread=1.0)
            elif war.t < war.sparking[tm]:
                emit(fxengine.EMBER, ox + b["x"] + random.uniform(-b["r"], b["r"]), oy + b["y"] + b["r"] * 0.5, 1,
                     GOLD, speed=(40, 120), life=(0.4, 0.8), size=(1.5, 3.5), angle=-math.pi / 2, spread=1.0)

    def draw_anims(img):
        keep = []
        for an in anims:
            age = war.t - an["t0"]
            if age < 0:
                keep.append(an)
                continue
            if age >= an["dur"]:
                continue
            a = age / an["dur"]
            size = an["s0"] + (an["s1"] - an["s0"]) * (1 - (1 - a) ** 2)
            if an["frames"]:                                     # flipbook : image suivante, pas de fondu
                fr_ = an["frames"][min(len(an["frames"]) - 1, int(a * len(an["frames"])))]
                sc_ = size / max(fr_.width, fr_.height)
                dx_, dy_ = (0.5 - an.get("ax", 0.5)) * fr_.width * sc_, (0.5 - an.get("ay", 0.5)) * fr_.height * sc_
                paste_center(img, fr_, an["x"] + dx_, an["y"] + dy_, size, an["al"], 0)
            else:
                paste_center(img, an["spr"], an["x"], an["y"], size, an["al"] * (1 - a) ** 1.3,
                             an["rot"] + an["spin"] * age)
            keep.append(an)
        anims[:] = keep

    def aura_img(team: int, h: int, gold: bool, phase: int):
        """Aura (library/_domain/fx/« <Perso> aura.png », sinon « aura.png », teintée) derrière le perso."""
        key = (team, h, gold, phase)
        if key not in auras:
            spr = None if gold else fx_sprite(None, names[team], "aura")
            own = spr is not None
            spr = spr if own else fx_sprite("aura")
            if spr is None:
                auras[key] = None
            else:
                sy = (1.0, 1.06, 0.96)[phase]
                im = spr.resize((max(4, int(h * spr.width / spr.height)), max(4, int(h * sy))), Image.BILINEAR)
                if not own or gold:                          # teinte : or (Sparking) ou couleur de la forme
                    col = GOLD if gold else hex_rgb(sheets[team].get("aura"), mix(cols[team], 0.35))
                    t_ = Image.new("RGBA", im.size, mix(col, 0.15) + (255,))
                    t_.putalpha(im.getchannel("A"))
                    im = t_
                auras[key] = im
        return auras[key]

    try:
        frames += intro()                                        # accroche : 1re seconde
        banners.append({"t0": 0.0, "team": -1, "who": "", "move": "FIGHT!", "big": True, "dur": 0.9, "cy": 0.45})
        finish_done = False
        while not finished(war, seconds):
            director.tick()
            if director.finish is not None and not finish_done:   # le dernier perso tombe → FINISH!
                finish_done = True
                frames += finish_cut(ox + director.finish[1], oy + director.finish[2], director.finish[3])
                banners.append({"t0": war.t, "team": -1, "who": "", "move": "FINISH!" if director.finish[3] >= 0
                                else "DRAW!", "big": True, "dur": 1.4, "cy": 0.45})
            for team in (0, 1):                                  # vient de se transformer → cinématique
                if war.transformed[team] is not None and not cine_done[team]:
                    cine_done[team] = True
                    frames += cinematic(team, last_img)
                    post_fx[0] = war.t                            # retour : flash + dézoom sur l'arène
            for team in (0, 1):                                  # formes intermédiaires : l'icône change + impact
                nxt = stage[team] + 1
                if (nxt < len(stages[team]) and war.t >= stage_t[team][nxt] and war.transformed[team] is None
                        and director.s1 is None):
                    stage[team] = nxt
                    stage_ev.append((war.t, team))
                    banners.append({"t0": war.t, "team": team, "who": names[team], "move": stages[team][nxt][0],
                                    "big": False})
                    for b in war.mains(team):
                        anim("burst", ox + b["x"], oy + b["y"], b["r"] * 2, b["r"] * 9, 0.5, mix(cols[team], 0.3),
                             spin=1.5)
                        anim("ring", ox + b["x"], oy + b["y"], b["r"] * 1.5, b["r"] * 8, 0.45, mix(cols[team], 0.3))
                        emit(fxengine.SPARK, ox + b["x"], oy + b["y"], 30, mix(cols[team], 0.5), speed=(300, 800))
                        tex.spawn("star_09", ox + b["x"], oy + b["y"], b["r"] * 2, 0.3, (255, 250, 230),
                                  size1=b["r"] * 7, hot=1.0)
                        tex.spawn("circle_02", ox + b["x"], oy + b["y"], b["r"], 0.45, mix(cols[team], 0.4),
                                  size1=b["r"] * 8, hot=0.7)
                        emit(fxengine.EMBER, ox + b["x"], oy + b["y"], 15, mix(cols[team], 0.3), speed=(60, 220),
                             life=(0.5, 1.0), angle=-math.pi / 2, spread=1.6)
            for t0, team, sp in [(t0, tm, True) for t0, tm in director.sparks[seen_sp:]]:
                banners.append({"t0": t0, "team": team, "who": names[team], "move": "SPARKING!", "big": False})
            seen_sp = len(director.sparks)
            for t0, team, slot, fx in director.events[seen:]:
                if fx.get("fam") == "none":
                    continue
                if slot == "clash":                              # Beam Clash : une seule bannière, en haut
                    if team == 0:
                        n1 = (sheets[1].get("front") or {}).get("name", "Beam")
                        banners = [b for b in banners if b["t0"] < t0 - 0.01]
                        banners.append({"t0": t0, "team": -1, "who": "BEAM CLASH!", "move": f"{fx['name']} vs {n1}",
                                        "big": True, "cy": 0.16, "dur": 3.4})
                    continue
                if fx.get("fam") == "clones" and slot == "secret":   # KAGE BUNSHIN : vague de clones
                    rl = random.Random(int(t0 * 1000))
                    foes = [(gx_, gy_) for gy_ in range(ny) for gx_ in range(nx) if war.grid[gy_][gx_] != team]
                    for j, b in enumerate(war.mains(team)):
                        poof(ox + b["x"], oy + b["y"], b["r"] * 2.2)
                        for q in range(4):
                            gx_, gy_ = rl.choice(foes) if foes else (rl.randrange(nx), rl.randrange(ny))
                            leapers.append((t0 + 0.05 + (j * 4 + q) * 0.07, team, ox + b["x"], oy + b["y"],
                                            ox + (gx_ + 0.5) * cell, oy + (gy_ + 0.5) * cell, b["r"]))
                    cam.punch(war.t, W / 2, oy + gh / 2, 0.04, 0.4)
                mvl = (fx.get("name") or "").lower()
                if mvl in eye_moves[team] and eyes_count.get((team, mvl), 0) < 2 and not war.final:
                    eyes_count[(team, mvl)] = eyes_count.get((team, mvl), 0) + 1
                    frames += eye_cut(team, last_img, fx["name"])
                final = t0 >= director.final_from - 0.01           # phase finale : bannières discrètes
                big = slot == "secret" and not final                 # seuls les secrets prennent le centre
                banners.append({"t0": t0, "team": team, "who": names[team], "move": fx["name"], "big": big})
                if fx.get("broke"):
                    banners.append({"t0": t0 + 1.3, "team": team, "who": names[team],
                                    "move": f"{fx['broke']} negated!", "big": False})
                if slot == "zone" and team == 1 and not clash_shown and t0 >= director.clash - 0.01:
                    clash_shown = True
                    fams = {sheets[0].get("zone", {}).get("fam"), sheets[1].get("zone", {}).get("fam")}
                    clash = "DOMAIN CLASH!" if fams <= {"domain", "shrine"} else "FINAL CLASH!"
                    banners = [b for b in banners if b["t0"] < t0 - 0.01]
                    banners.append({"t0": t0, "team": -1, "who": "", "move": clash, "big": True})
            seen = len(director.events)
            slow = 1.0                                           # ralenti : fin du Beam Clash, K.O. en phase finale
            if war.beam and (war.t - war.beam["t0"]) / war.beam["dur"] > 0.72:
                slow = 0.45
            elif any(0 <= war.t - t0 < 0.5 for t0, *_ in director.kos[-1:]) and war.final:
                slow = 0.5
            for _ in range(4):
                war.step(1 / fps / 4 * slow)
            if slow < 1:
                pauses.append((war.t, (1 - slow) / fps))
            parts.step(1 / fps * slow)
            tex.step(1 / fps * slow)
            vfx_frame()
            img = bg.copy()
            d = ImageDraw.Draw(img)
            for gy in range(ny):                                 # terrain : cases texturées en relief
                row = war.grid[gy]
                for gx in range(nx):
                    fl = min(4, int(war.flash[gy][gx] * 4 + 0.5))
                    img.paste(tile(row[gx], (gx * 7 + gy * 13) % 4, fl),
                              (int(ox + gx * cell) + 1, int(oy + gy * cell) + 1))
            keep_d = []
            for t0, x, y, R, rot in decals:                      # cratères / brûlures (8 s, puis s'effacent)
                age = war.t - t0
                if age < 8:
                    paste_center(img, scorch, x, y, R * 2 * min(1.0, 0.6 + age * 4),
                                 0.8 * min(1.0, (8 - age) / 3), rot)
                    keep_d.append((t0, x, y, R, rot))
            decals[:] = keep_d
            for t0, lx, ly in logs:                              # bûches (1,2 s puis disparaissent)
                if 0 <= war.t - t0 < 1.2:
                    paste_center(img, log_img, lx, ly, cell * 2.6, min(1.0, (1.2 - (war.t - t0)) / 0.3), -20)
            keep_b = []
            ama = fx_sprite("Amaterasu") if burns else None
            for t0, bx, by, sd in burns:                         # Amaterasu : feu noir qui ne s'éteint pas
                age = war.t - t0
                if age >= BURN_S:
                    continue
                keep_b.append((t0, bx, by, sd))
                life = min(1.0, age / 0.25) * min(1.0, (BURN_S - age) / 1.5)
                glow_ = Image.new("RGBA", (int(cell * 6), int(cell * 6)), (0, 0, 0, 0))
                ImageDraw.Draw(glow_).ellipse((0, 0, glow_.width, glow_.height), fill=(110, 30, 160, int(110 * life)))
                glow_ = glow_.filter(ImageFilter.GaussianBlur(cell * 0.8))
                img.alpha_composite(glow_, (int(bx - glow_.width / 2), int(by - glow_.height / 2)))
                if ama is not None:
                    for j in range(2):                           # 2 couches qui ondulent = flammes vivantes
                        fl = 1 + 0.12 * math.sin(age * 9 + j * 2.1 + sd * 6)
                        sp_ = ama if j == 0 else ama.transpose(Image.FLIP_LEFT_RIGHT)
                        paste_center(img, sp_, bx + (j - 0.5) * cell * 0.8, by - cell * 0.6 * fl,
                                     cell * (4.2 if j == 0 else 3.4) * fl, 0.95 * life, math.sin(age * 3 + j) * 0.06)
                rb = random.Random(int(war.t * fps) * 31 + int(sd * 1000))
                if rb.random() < 0.5:                            # fumée noire et flammes qui montent
                    tex.spawn(rb.choice(("flame_01", "flame_02", "flame_05")), bx + rb.uniform(-1, 1) * cell * 1.4,
                              by + rb.uniform(-0.5, 0.5) * cell, cell * 2.0, 0.8, (16, 5, 24), size1=cell * 3.2,
                              vy=-50 * k, glow=False, hot=0, alpha=0.9 * life)
            burns[:] = keep_b
            ground = Image.new("RGBA", (W, H), (0, 0, 0, 0))     # débris + poussière (pas lumineux)
            parts.draw(ground, kinds=(fxengine.DEBRIS, fxengine.SMOKE))
            tex.draw(ground, glow=False)                         # fumée / terre texturées
            img.alpha_composite(ground)
            fxl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            fd = ImageDraw.Draw(fxl)
            fw_ = max(2, int(cell * 0.16))                      # ligne de front lumineuse entre les 2 domaines
            for gy in range(ny):
                row = war.grid[gy]
                nxt_row = war.grid[gy + 1] if gy + 1 < ny else None
                for gx in range(nx):
                    x0, y0 = ox + gx * cell, oy + gy * cell
                    if gx + 1 < nx and row[gx + 1] != row[gx]:
                        fd.line((x0 + cell, y0, x0 + cell, y0 + cell), fill=(255, 255, 255, 150), width=fw_)
                    if nxt_row is not None and nxt_row[gx] != row[gx]:
                        fd.line((x0, y0 + cell, x0 + cell, y0 + cell), fill=(255, 255, 255, 150), width=fw_)
            sprites = []                                         # images d'attaques (library/_domain/fx/) par-dessus
            for fx in war.fx:
                age = war.t - fx["t0"]
                fam, c = fx["fam"], mix(cols[fx["team"]], 0.45)
                spr = atk_at(fx.get("name"), fx["team"], fx.get("slot"), war.t - fx["t0"]) if fx.get("name") else None
                if fam == "bomb":
                    if age < fx["delay"]:                      # la sphère tombe du haut
                        a = age / fx["delay"]
                        x, y = ox + fx["tx"], oy + fx["ty"] * a * a
                        R = fx["radius"] * 0.6
                        if spr is not None:
                            sprites.append(("c", spr, x, y, R * 2.4, 1.0, 0))
                            continue
                        fd.ellipse((x - R, y - R, x + R, y + R), fill=c + (200,), outline=(255, 255, 255, 230),
                                   width=int(cell * 0.4))
                    else:
                        a = min(1, (age - fx["delay"]) / 0.4)
                        R = fx["radius"] * a
                        al = int(255 * max(0, 1 - (age - fx["delay"]) / 1.0))
                        x, y = ox + fx["tx"], oy + fx["ty"]
                        fd.ellipse((x - R, y - R, x + R, y + R), outline=(255, 255, 255, al), width=int(cell * 0.6))
                elif fam in ("domain", "shrine"):
                    b = fx["ball"]
                    a = min(1, age / fx["dur"])
                    R = fx["radius"] * a
                    al = int(200 * max(0, 1 - max(0, age - 1.0) / 0.4))
                    x, y = ox + b["x"], oy + b["y"]
                    fd.ellipse((x - R, y - R, x + R, y + R), fill=c + (al // 3,), outline=c + (al,),
                               width=int(cell * 0.5))
                    if fam == "shrine" and fx_sprite("slash_1") is None:   # entailles (sans images)
                        rr = random.Random(int(fx["t0"] * 1000) + int(age * 12))
                        for _ in range(7):
                            px, py = x + rr.uniform(-R, R) * 0.8, y + rr.uniform(-R, R) * 0.8
                            an = rr.uniform(0, math.pi)
                            L = cell * 2.5
                            fd.line((px - math.cos(an) * L, py - math.sin(an) * L, px + math.cos(an) * L,
                                     py + math.sin(an) * L), fill=(255, 255, 255, al), width=int(cell * 0.25))
                elif fam in ("beam", "mega_beam"):
                    L = fx["length"] * min(1, age / fx["dur"])
                    al = max(0.0, 1 - age / 1.1)
                    x1, y1 = ox + fx["x"], oy + fx["y"]
                    x2, y2 = x1 + math.cos(fx["ang"]) * L, y1 + math.sin(fx["ang"]) * L
                    w = cell * (2 * fx["half"] + 1)
                    if spr is None:
                        spr = pack_beam(fx["team"], L, w * 3.2, age, fx.get("name"))
                        if spr is not None:                      # pack : rayon net par-dessus le halo
                            al_ = min(1.0, max(0.0, (1.1 - age) / 0.35))
                            sprites.append(("b", spr, x1, y1, x2, y2, w * 3.2, al_ * 0.6))
                            crisp_b.append((spr, x1, y1, x2, y2, w * 3.2, al_))
                            continue
                    if spr is not None:
                        sprites.append(("b", spr, x1, y1, x2, y2, w * 2.2, min(1.0, max(0.0, (1.1 - age) / 0.35))))
                        continue
                    fd.line((x1, y1, x2, y2), fill=c + (int(220 * al),), width=int(w))
                    fd.line((x1, y1, x2, y2), fill=(255, 255, 255, int(255 * al)), width=int(w * 0.4))
                elif fam == "shots":
                    b = fx["ball"]
                    for i, (tx, ty) in enumerate(fx["shots"]):
                        a = (age - i * 0.05) / 0.3
                        if 0 <= a < 1:
                            x = ox + b["x"] + (tx - b["x"]) * a
                            y = oy + b["y"] + (ty - b["y"]) * a
                            R = cell * 0.6
                            if spr is not None:
                                sz_ = cell * (4.0 if PACK and spr.width % 4 == 0 and spr.width <= 320 else 2.4)
                                sprites.append(("c", spr, x, y, sz_, 1.0, math.atan2(ty - b["y"], tx - b["x"])))
                                continue
                            fd.ellipse((x - R, y - R, x + R, y + R), fill=(255, 255, 255, 255), outline=c + (255,),
                                       width=int(cell * 0.3))
                        elif 1 <= a < 2.2:
                            R = cell * 1.8 * min(1, (a - 1) * 3)
                            x, y = ox + tx, oy + ty
                            fd.ellipse((x - R, y - R, x + R, y + R), outline=(255, 255, 255, int(255 * (2.2 - a) / 1.2)),
                                       width=int(cell * 0.3))
                elif fam == "teleport" and age < 0.8 and "radius" in fx:
                    x, y = ox + fx["x"], oy + fx["y"]
                    R = fx["radius"] * min(1, age / 0.3)
                    fd.ellipse((x - R, y - R, x + R, y + R), outline=(255, 255, 255, int(255 * (1 - age / 0.8))),
                               width=int(cell * 0.5))
                elif fam == "vanish" and age < 0.6:              # Vanish : image rémanente + coup derrière
                    al = 1 - age / 0.6
                    x0, y0, x, y = ox + fx["x0"], oy + fx["y0"], ox + fx["x"], oy + fx["y"]
                    rb = fx["ball"]["r"]
                    for j in range(4):
                        q = j / 4
                        gx_, gy_ = x0 + (x - x0) * q, y0 + (y - y0) * q
                        fd.ellipse((gx_ - rb, gy_ - rb, gx_ + rb, gy_ + rb),
                                   outline=c + (int(160 * al * (1 - q)),), width=int(cell * 0.3))
                    fd.line((x0, y0, x, y), fill=(255, 255, 255, int(200 * al)), width=int(cell * 0.35))
                    R = fx["radius"] * min(1, age / 0.25)
                    fd.ellipse((x - R, y - R, x + R, y + R), outline=(255, 255, 255, int(255 * al)), width=int(cell * 0.5))
                elif fam == "regen" and age < 0.5:
                    b = fx["ball"]
                    R = cell * 1.9 * (age / 0.5)
                    x, y = ox + b["x"], oy + b["y"]
                    fd.ellipse((x - R, y - R, x + R, y + R), outline=mix(cols[fx["team"]], 0.7) + (int(200 * (1 - age / .5)),),
                               width=int(cell * 0.2))
            crisp = []                                           # boules du Beam Clash, nettes par-dessus le halo
            crisp_b = []                                         # rayons du pack, nets par-dessus le halo
            bc = war.beam
            if bc:                                               # Beam Clash : 2 rayons qui se poussent
                age = war.t - bc["t0"]
                y = oy + bc["y"]
                xm = ox + bc["pos"] * gw
                th = cell * (2 * bc["half"] + 1) * 0.95 * (1 + 0.08 * math.sin(age * 40))
                grow = min(1.0, age / 0.35)
                xl, xr = ox + (xm - ox) * grow, ox + gw - (ox + gw - xm) * grow
                for x1, x2, tm in ((ox, xl, 0), (xr, ox + gw, 1)):
                    spr = atk_at((sheets[tm].get("front") or {}).get("name"), tm, "front", age)
                    if spr is None:
                        spr = pack_beam(tm, abs(x2 - x1), th * 3.2, age, (sheets[tm].get("front") or {}).get("name"))
                        if spr is not None:
                            pts_ = (x1, y, x2, y) if tm == 0 else (x2, y, x1, y)
                            sprites.append(("b", spr, *pts_, th * 3.2, 0.6))
                            crisp_b.append((spr, *pts_, th * 3.2, 1.0))
                            continue
                    if spr is not None and spr.width < spr.height * 1.6:   # Rasengan / Chidori : boule tenue en main
                        BR = th * 3.4 * (1 + 0.06 * math.sin(age * 31 + tm))
                        bxx = (x2 - BR * 0.36) if tm == 0 else (x1 + BR * 0.36)
                        fd.line((x1, y, x2, y), fill=mix(cols[tm], 0.25) + (200,), width=int(th * 0.55))
                        fd.line((x1, y, x2, y), fill=(255, 255, 255, 230), width=int(th * 0.2))
                        sprites.append(("c", spr, bxx, y, BR, 1.0, age * (9 if tm == 0 else -4)))
                        crisp.append((spr, bxx, y, BR * 0.92, age * (9 if tm == 0 else -4)))
                        continue
                    if spr is not None:                          # rayon dessiné du lanceur vers le centre
                        sprites.append(("b", spr, x1, y, x2, y, th * 2.2, 1.0) if tm == 0 else
                                       ("b", spr, x2, y, x1, y, th * 2.2, 1.0))
                        continue
                    fd.line((x1, y, x2, y), fill=mix(cols[tm], 0.25) + (235,), width=int(th))
                    fd.line((x1, y, x2, y), fill=(255, 255, 255, 255), width=int(th * 0.4))
                if grow >= 1:
                    R = th * ((0.32 if crisp else 0.62) + 0.15 * math.sin(age * 23))
                    fd.ellipse((xm - R, y - R, xm + R, y + R), fill=(255, 255, 255, 255), outline=GOLD + (255,),
                               width=int(cell * 0.4))
                    rr = random.Random(int(age * 30))
                    for _ in range(8):
                        an = rr.uniform(0, 2 * math.pi)
                        L = th * rr.uniform(1.2, 2.6)
                        fd.line((xm, y, xm + math.cos(an) * L, y + math.sin(an) * L), fill=GOLD + (220,),
                                width=int(cell * 0.25))
            img.alpha_composite(fxl.filter(ImageFilter.GaussianBlur(3)))
            img.alpha_composite(fxl)
            if sprites:                                          # attaques : couche d'énergie + halo (bloom)
                energy = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                for sp_ in sprites:
                    if sp_[0] == "b":
                        paste_beam(energy, sp_[1], *sp_[2:6], sp_[6], sp_[7])
                    else:
                        paste_center(energy, sp_[1], sp_[2], sp_[3], sp_[4], sp_[5], sp_[6])
                img = fxengine.bloom(img, energy, 0.8)
                for spr_, cx_, cy_, sz_, rot_ in crisp:
                    paste_center(img, spr_, cx_, cy_, sz_, 1.0, rot_)
                for spr_, *pts_, w_, al_ in crisp_b:
                    paste_beam(img, spr_, *pts_, w_, al_)
            if war.timestop:                                     # temps arrêté : grille en négatif violacé
                region = (int(ox), int(oy), int(ox + gw), int(oy + gh))
                reg = img.crop(region).convert("RGB")
                from PIL import ImageOps
                inv = ImageOps.invert(reg).convert("RGBA")
                tint = Image.new("RGBA", inv.size, (120, 60, 200, 90))
                inv.alpha_composite(tint)
                img.paste(inv, region[:2])
            d = ImageDraw.Draw(img)
            for b in war.balls:
                if b["team"] == 0 or True:
                    for j, (tx, ty) in enumerate(b["trail"]):
                        rr = b["r"] * (0.4 + 0.5 * j / max(1, len(b["trail"])))
                        d.ellipse((ox + tx - rr, oy + ty - rr, ox + tx + rr, oy + ty + rr),
                                  fill=mix(cols[b["team"]], 0.4))
            for b in war.balls:
                r = b["r"]
                x, y = ox + b["x"], oy + b["y"]
                trans = war.transformed[b["team"]] is not None
                if b["kind"] == "summon":
                    nm = [e for e in director.events if e[1] == b["team"] and e[2] == "secret"]
                    sname = nm[-1][3].get("summon", "?") if nm else "?"
                    if sname not in summons:
                        summons[sname] = _summon_icon(sname, cols[b["team"]])
                    im = ic(("s", sname), summons[sname], 2 * r)
                else:
                    tf = war.transformed[b["team"]] is not None and forms[b["team"]] is not None
                    im = ic((b["team"], tf, stage[b["team"]]), face(b["team"]), 2 * r)
                    if tf and b["kind"] == "main" and war.t - war.transformed[b["team"]] < 0.6:   # onde de transfo
                        a = (war.t - war.transformed[b["team"]]) / 0.6
                        rr = r * (1.2 + 2.2 * a)
                        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=mix(cols[b["team"]], 0.6),
                                  width=max(2, int(cell * 0.5 * (1 - a))))
                pa = None                                        # aura du pack (2 couches) : Sparking, ou forme
                if b["kind"] == "main" and (war.t < war.sparking[b["team"]] or trans) and PACK \
                        and (not trans or fx_sprite(None, names[b["team"]], "aura") is None):
                    gold_ = not trans
                    eid_ = "aura_ki" if gold_ else str(sheets[b["team"]].get("vfx_aura") or "aura_blaze")
                    col_ = GOLD if gold_ else hex_rgb(sheets[b["team"]].get("aura"), mix(cols[b["team"]], 0.35))
                    back_, front_ = packfx(eid_, col_, "back"), packfx(eid_, col_, "front")
                    if back_:                                    # flammes élargies pour envelopper l'icône ronde
                        fi_ = int(war.t * vfxpack.fps()) % len(back_)
                        ah_ = r * 6.5
                        aw_ = ah_ * 112 / 144 * 2.3
                        fx_, fy_ = vfxpack.anchor(eid_)
                        pa = (front_[fi_ % len(front_)] if front_ else None, aw_, ah_, fy_)
                        bf_ = back_[fi_].resize((int(aw_), int(ah_)), Image.NEAREST)
                        img.alpha_composite(bf_, (int(x - aw_ / 2), int(y + r * 1.3 - fy_ * ah_)))
                        d = ImageDraw.Draw(img)
                elif b["kind"] == "main" and (war.t < war.sparking[b["team"]] or trans):   # aura derrière le perso
                    au = aura_img(b["team"], int(r * 4.6), not trans, int(war.t * 14) % 3)
                    if au is not None:
                        img.alpha_composite(au, (int(x - au.width / 2), int(y - au.height * 0.62)))
                        d = ImageDraw.Draw(img)
                if b["kind"] == "main" and war.t < war.sparking[b["team"]]:   # SPARKING : aura dorée
                    for j in range(3):
                        rr_ = r * (1.25 + 0.22 * j + 0.08 * math.sin(war.t * 18 + j))
                        d.ellipse((x - rr_, y - rr_, x + rr_, y + rr_), outline=mix(GOLD, 0.25 * j),
                                  width=max(2, int(cell * 0.28)))
                if war.t - b["hurt"] < 0.35:                     # touché : flash rouge + tremblement
                    im = im.copy()
                    red = Image.new("RGBA", im.size, (255, 30, 30, 255))
                    red.putalpha(im.getchannel("A").point(lambda v: v * 6 // 10))
                    im = Image.alpha_composite(im, red)
                    x += math.sin(war.t * 90) * cell * 0.35
                if b["kind"] == "clone":                         # clone : presque opaque, liseré de chakra
                    im = im.copy()
                    im.putalpha(im.getchannel("A").point(lambda v: v * 85 // 100))
                    rr_ = r * (1.12 + 0.06 * math.sin(war.t * 16 + b["id"]))
                    d.ellipse((x - rr_, y - rr_, x + rr_, y + rr_), outline=mix(cols[b["team"]], 0.35),
                              width=max(2, int(cell * 0.22)))
                if war.t < b["frozen_until"]:                    # figé : gris + anneau
                    g = im.convert("LA").convert("RGBA")
                    g.putalpha(im.getchannel("A"))
                    im = g
                img.alpha_composite(im, (int(x - r), int(y - r)))
                if pa is not None and pa[0] is not None:          # couche avant de l'aura (par-dessus le perso)
                    ff_, aw_, ah_, fy_ = pa
                    ff_ = ff_.resize((int(aw_), int(ah_)), Image.NEAREST)
                    ff_.putalpha(ff_.getchannel("A").point(lambda v: v * 6 // 10))
                    img.alpha_composite(ff_, (int(x - aw_ / 2), int(y + r * 1.3 - fy_ * ah_)))
                    d = ImageDraw.Draw(img)
                if war.t < b["frozen_until"]:
                    d.ellipse((x - r - 4, y - r - 4, x + r + 4, y + r + 4), outline=(200, 230, 255), width=int(4 * k))
                if b["kind"] == "main" and war.passive_on(b["team"], "infinity"):   # Infini : anneau
                    R = cell * 2.8
                    d.ellipse((x - R, y - R, x + R, y + R), outline=mix(cols[b["team"]], 0.7), width=max(2, int(3 * k)))
                if b["kind"] == "main":                          # barre de vie (3 PV)
                    bw, bh_ = r * 2.1, max(8, int(cell * 0.5))
                    bx, byy = x - bw / 2, y - r - bh_ - 6 * k
                    d.rectangle((bx - 2, byy - 2, bx + bw + 2, byy + bh_ + 2), fill=(0, 0, 0))
                    hp = max(0, b["hp"])
                    hc = ((230, 60, 60), (240, 190, 40), (70, 220, 90))[max(0, hp - 1)]
                    seg = bw / 3
                    for j in range(3):
                        d.rectangle((bx + j * seg + 1, byy, bx + (j + 1) * seg - 1, byy + bh_),
                                    fill=hc if j < hp else (60, 60, 70))
            spawn_anims()
            energy = Image.new("RGBA", (W, H), (0, 0, 0, 0))     # effets + particules : additif + halo
            draw_anims(energy)
            parts.draw(energy)
            tex.draw(energy, glow=True)                          # feu, éclairs, traînées, flammes d'aura
            img = fxengine.bloom(img, energy, 0.9)
            img.alpha_composite(vig)
            d = ImageDraw.Draw(img)
            share = war.share()
            by, bh = oy + gh + 30 * k, 64 * k
            d.rounded_rectangle((ox, by, ox + gw, by + bh), radius=bh / 2, fill=cols[1])
            d.rounded_rectangle((ox, by, ox + max(bh, gw * share), by + bh), radius=bh / 2, fill=cols[0])
            d.text((ox + 28 * k, by + bh / 2), f"{share * 100:.0f}%", font=pf, anchor="lm", fill=(255, 255, 255),
                   stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
            d.text((ox + gw - 28 * k, by + bh / 2), f"{(1 - share) * 100:.0f}%", font=pf, anchor="rm",
                   fill=(255, 255, 255), stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
            for i, (al, x) in enumerate((("la", ox), ("ra", ox + gw))):
                d.text((x, by + bh + 14 * k), names[i].upper(), font=nf, anchor=al, fill=cols[i],
                       stroke_width=int(2 * k), stroke_fill=(0, 0, 0))
                pas = sheets[i].get("passive", {})
                if pas.get("fam", "none") != "none":
                    off = war.t < war.passive_off[i]
                    txt = f"{'✕ ' if off else ''}{pas['name']}"
                    d.text((x, by + bh + 64 * k), txt, font=sf, anchor=al,
                           fill=(120, 120, 130) if off else mix(cols[i], 0.5))
            for i in (0, 1):                                     # jauge de Ki (pleine → SPARKING)
                kw, kh, ky = gw * 0.42, 20 * k, by + bh + 118 * k
                kx = ox if i == 0 else ox + gw - kw
                spk = war.t < war.sparking[i]
                fr_ = 1.0 if spk else war.ki[i] / 100
                d.rounded_rectangle((kx, ky, kx + kw, ky + kh), radius=kh / 2, fill=(35, 35, 48))
                fw = kw * fr_
                if fw > kh:
                    x1 = kx if i == 0 else kx + kw - fw
                    fc = mix(GOLD, 0.35 * (0.5 + 0.5 * math.sin(war.t * 20))) if spk else mix(cols[i], 0.25)
                    d.rounded_rectangle((x1, ky, x1 + fw, ky + kh), radius=kh / 2, fill=fc)
                lab = "SPARKING!" if spk else str(sheets[i].get("gauge") or "KI").upper()   # CHAKRA pour Naruto…
                d.text((kx if i == 0 else kx + kw, ky + kh + 6 * k), lab, font=sf,
                       anchor="la" if i == 0 else "ra", fill=GOLD if spk else (150, 155, 170))
                smax = int(sheets[i].get("substitute") or 0)
                if smax:                                         # permutations restantes (barres jaunes, Storm)
                    lw = render.text_width(d, lab, sf)
                    sw_, sh_, gap = 26 * k, 12 * k, 6 * k
                    for j in range(smax):
                        on = j < war.subs_left[i]
                        x0_ = (kx + lw + 16 * k + j * (sw_ + gap)) if i == 0 else (kx + kw - lw - 16 * k - (j + 1) * sw_ - j * gap)
                        y0_ = ky + kh + 6 * k + (sf.size - sh_) / 2
                        d.rounded_rectangle((x0_, y0_, x0_ + sw_, y0_ + sh_), radius=3 * k,
                                            fill=(255, 205, 40) if on else (55, 55, 66))
            if bc:                                               # jauge du Beam Clash
                gw2, gh2 = gw * 0.86, 46 * k
                gx2, gy2 = ox + (gw - gw2) / 2, oy + gh * 0.1
                d.rounded_rectangle((gx2 - 4, gy2 - 4, gx2 + gw2 + 4, gy2 + gh2 + 4), radius=gh2 / 2, fill=(0, 0, 0))
                d.rounded_rectangle((gx2, gy2, gx2 + gw2, gy2 + gh2), radius=gh2 / 2, fill=cols[1])
                d.rounded_rectangle((gx2, gy2, gx2 + max(gh2, gw2 * bc["pos"]), gy2 + gh2), radius=gh2 / 2,
                                    fill=cols[0])
                mx = gx2 + gw2 * bc["pos"]
                d.polygon(((mx, gy2 + gh2 + 4), (mx - 16 * k, gy2 + gh2 + 26 * k), (mx + 16 * k, gy2 + gh2 + 26 * k)),
                          fill=GOLD)
                d.rectangle((mx - 4 * k, gy2 - 6 * k, mx + 4 * k, gy2 + gh2 + 6 * k), fill=(255, 255, 255))
                mf = render.font(int(40 * k))                    # « MASH ○ » façon choc de jutsu Naruto Storm
                for i_ in (0, 1):
                    on = int((war.t + i_ * 0.07) * 14) % 2 == 0
                    bx_ = gx2 + gw2 * (0.16 if i_ == 0 else 0.84)
                    by_ = oy + gh * 0.88                          # en bas de l arène (le titre du choc est en haut)
                    rr_ = (30 if on else 26) * k
                    d.ellipse((bx_ - rr_, by_ - rr_, bx_ + rr_, by_ + rr_), fill=(255, 255, 255) if on else cols[i_],
                              outline=(0, 0, 0), width=int(4 * k))
                    d.ellipse((bx_ - rr_ * 0.45, by_ - rr_ * 0.45, bx_ + rr_ * 0.45, by_ + rr_ * 0.45),
                              outline=cols[i_] if on else (255, 255, 255), width=int(5 * k))
                    d.text((bx_ + (rr_ + 10 * k) * (1 if i_ == 0 else -1), by_), "MASH!", font=mf,
                           anchor="lm" if i_ == 0 else "rm", fill=GOLD if on else (255, 255, 255),
                           stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
            keep_l = []
            for lp in leapers:                                   # clones en vol (arc) → impact + pouf à l'arrivée
                t0, tm, sx, sy, tx_, ty_, r = lp
                a = (war.t - t0) / LEAP
                if a < 0:
                    keep_l.append(lp)
                    continue
                if a >= 1:
                    leap_land.append(war.t)
                    poof(tx_, ty_, r * 1.4)
                    tex.spawn("star_08", tx_, ty_, r * 1.5, 0.18, mix(cols[tm], 0.5), size1=r * 4, hot=1.0)
                    emit(fxengine.SPARK, tx_, ty_, 10, mix(cols[tm], 0.5), speed=(200, 600))
                    emit(fxengine.DEBRIS, tx_, ty_, 4, (90, 80, 70), speed=(80, 260))
                    continue
                keep_l.append(lp)
                e = 1 - (1 - a) ** 2
                lx, ly = sx + (tx_ - sx) * e, sy + (ty_ - sy) * e - math.sin(math.pi * a) * cell * 5
                sz = int(r * 2 * (1 + 0.35 * math.sin(math.pi * a)))
                cim = ic((tm, war.transformed[tm] is not None and forms[tm] is not None, stage[tm]), face(tm), sz)
                for g_ in range(3):                              # traînée
                    a2 = max(0.0, a - 0.06 * (g_ + 1))
                    e2 = 1 - (1 - a2) ** 2
                    gx2_, gy2_ = sx + (tx_ - sx) * e2, sy + (ty_ - sy) * e2 - math.sin(math.pi * a2) * cell * 5
                    d.ellipse((gx2_ - sz * 0.3, gy2_ - sz * 0.3, gx2_ + sz * 0.3, gy2_ + sz * 0.3),
                              fill=mix(cols[tm], 0.4 + 0.15 * g_))
                img.alpha_composite(cim, (int(lx - cim.width / 2), int(ly - cim.height / 2)))
                d = ImageDraw.Draw(img)
            leapers[:] = keep_l
            for t0, mx_, my_, team in war.misses:                 # esquive : « MISS! »
                age = war.t - t0
                if 0 <= age < 0.8:
                    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    a = int(255 * min(1.0, (0.8 - age) / 0.3))
                    ImageDraw.Draw(ov).text((ox + mx_, oy + my_ - cell * 2 - age * 70 * k), "MISS!",
                                            font=render.font(int(48 * k)), anchor="mm", fill=(255, 255, 255, a),
                                            stroke_width=int(4 * k), stroke_fill=cols[team] + (a,))
                    img.alpha_composite(ov)
            for t0, team, kx, ky in director.kos:                 # « K.O. » quand un perso sort
                age = war.t - t0
                if age < 1.2:
                    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    a = int(255 * (1 - age / 1.2))
                    ImageDraw.Draw(ov).text((ox + kx, oy + ky - age * 60 * k), "K.O.", font=render.font(int(70 * k)),
                                            anchor="mm", fill=(255, 255, 255, a), stroke_width=int(5 * k),
                                            stroke_fill=cols[team] + (a,))
                    img.alpha_composite(ov)
            d = ImageDraw.Draw(img)
            small = [b for b in banners if not b["big"] and b["team"] >= 0 and 0 <= war.t - b["t0"] < 1.3]
            if small:                                             # attaques normales : petite étiquette en haut
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))     # de l'arène, le terrain reste visible
                od = ImageDraw.Draw(ov)
                for j, b in enumerate(small[-2:][::-1]):          # 2 max (une par camp), la plus récente dessus
                    age = war.t - b["t0"]
                    a = min(1.0, (1.3 - age) / 0.3) * min(1.0, age / 0.08)
                    move = b["move"].upper()
                    if move.replace("-", "").replace("!", "") == "KAMEHAMEHA":
                        sy = ["KA", "ME", "HA", "ME", "HA!"]
                        move = "-".join(sy[:min(5, int(age / 0.13) + 1)])
                    txt = f"{b['who'].split()[-1].upper()} · {move}" if b["who"] else move
                    f_ = render.font(int(36 * k))
                    while f_.size > 20 and render.text_width(od, txt, f_) > gw * 0.9:
                        f_ = render.font(f_.size - 2)
                    tw = render.text_width(od, txt, f_)
                    x_ = ox + 14 * k if b["team"] == 0 else ox + gw - 14 * k - tw - 28 * k
                    y_ = oy + 12 * k + j * 56 * k
                    c_ = mix(cols[b["team"]], 0.35)
                    od.rounded_rectangle((x_, y_, x_ + tw + 28 * k, y_ + 46 * k), radius=23 * k,
                                         fill=(0, 0, 0, int(150 * a)), outline=c_ + (int(220 * a),), width=max(2, int(3 * k)))
                    od.text((x_ + 14 * k, y_ + 23 * k), txt, font=f_, anchor="lm", fill=c_ + (int(255 * a),))
                img.alpha_composite(ov)
                d = ImageDraw.Draw(img)
            live = [b for b in banners if (b["big"] or b["team"] < 0) and
                    0 <= war.t - b["t0"] < b.get("dur", 2.0 if b["big"] else 1.4)]
            if live:                                              # secrets / chocs : gros texte au centre
                b = live[-1]
                age = war.t - b["t0"]
                dur = b.get("dur", 2.0 if b["big"] else 1.4)
                a = min(1.0, (dur - age) / 0.4)
                pop = 1 + 0.3 * max(0, 1 - age / 0.15)
                size = (88 if b["big"] else 70) * k * pop
                col = (255, 214, 10) if b["team"] < 0 else mix(cols[b["team"]], 0.3)
                bfont = render.font(int(size))
                move = b["move"].upper()
                if move.replace("-", "").replace("!", "") == "KAMEHAMEHA":     # « KA-ME-HA-ME-HA! » syllabe par syllabe
                    sy = ["KA", "ME", "HA", "ME", "HA!"]
                    move = "-".join(sy[:min(5, int(age / 0.13) + 1)])
                while bfont.size > 30 and render.text_width(d, move, bfont) > W * 0.92:
                    bfont = render.font(bfont.size - 4)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                cy = oy + gh * b.get("cy", 0.45)
                if b["who"]:
                    od.text((W / 2, cy - bfont.size * 0.85), b["who"].upper(), font=render.font(int(44 * k)),
                            anchor="mm", fill=col + (int(255 * a),), stroke_width=int(4 * k),
                            stroke_fill=(0, 0, 0, int(255 * a)))
                od.text((W / 2, cy), move, font=bfont, anchor="mm", fill=col + (int(255 * a),),
                        stroke_width=int(7 * k), stroke_fill=(0, 0, 0, int(255 * a)))
                img.alpha_composite(ov)
                if b["big"] and age < 0.12:                       # flash sur les secrets
                    img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(150 * (1 - age / 0.12)))))
            shake = 0.0                                          # l'écran tremble sur les gros coups
            for b in banners:
                ag = war.t - b["t0"]
                if b["big"] and 0 <= ag < 0.45:
                    shake = max(shake, 14 * k * (1 - ag / 0.45))
            for fx in war.fx:
                if fx["fam"] == "bomb":
                    ag = war.t - fx["t0"] - fx.get("delay", 0)
                    if 0 <= ag < 0.4:
                        shake = max(shake, 18 * k * (1 - ag / 0.4))
            for t0, *_ in director.kos:
                if 0 <= war.t - t0 < 0.3:
                    shake = max(shake, 12 * k)
            if war.beam:
                shake = max(shake, 5 * k)
            if PROC:
                keep_r = []
                for t0_, rx_, ry_ in ripples:                    # onde de choc : l'image se déforme en anneau
                    ag = war.t - t0_
                    if ag < 0.42:
                        keep_r.append((t0_, rx_, ry_))
                        img = fxengine.ripple(img, rx_, ry_, cell * (1 + 22 * ag), cell * 0.9 * (1 - ag / 0.42),
                                              cell * 1.6)
                ripples[:] = keep_r
            img = cam.apply(img, war.t, shake, seed=frames)
            pf_ = war.t - post_fx[0]
            if 0 <= pf_ < 0.35:                                   # retour de cinématique : dézoom + flash blanc
                z_ = 1 + 0.35 * (1 - pf_ / 0.35) ** 2
                w_, h_ = W / z_, H / z_
                img = img.crop((int((W - w_) / 2), int((H - h_) / 2), int((W + w_) / 2), int((H + h_) / 2))).resize((W, H), Image.BILINEAR)
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(230 * max(0.0, 1 - pf_ / 0.2)))))
            if 0 <= war.t - hit["chroma"] < 0.18:                 # énorme impact : aberration chromatique
                img = fxengine.chroma(img, int(7 * k * (1 - (war.t - hit["chroma"]) / 0.18)))
            proc.stdin.write(img.convert("RGB").tobytes())
            last_img = img
            frames += 1
            if hit["stop"]:                                      # arrêt sur impact : l'image reste figée
                for j_ in range(hit["stop"]):                    # 1re image = « impact frame » d'anime (2 tons)
                    fr_ = fxengine.impact_frame(img, hit.get("col", (255, 255, 255)), invert=j_ == 1) \
                        if j_ < 2 and PROC else img
                    proc.stdin.write(fr_.convert("RGB").tobytes())
                frames += hit["stop"]
                pauses.append((war.t, hit["stop"] / fps))
                hit["stop"] = 0
        win = 0 if war.share() >= 0.5 else 1
        win_at = frames / fps
        final_share = war.share() if win == 0 else 1 - war.share()
        draw = director.draw
        for f in range(int(fps * END_S) if draw else 0):           # ÉGALITÉ : les 2 visages, « Who really won? »
            img = Image.new("RGBA", (W, H), (14, 12, 22, 255))
            g2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            gd2 = ImageDraw.Draw(g2)
            gd2.polygon(((0, 0), (W * 0.55, 0), (W * 0.45, H), (0, H)), fill=cols[0] + (120,))
            gd2.polygon(((W * 0.55, 0), (W, 0), (W, H), (W * 0.45, H)), fill=cols[1] + (120,))
            img.alpha_composite(g2.filter(ImageFilter.GaussianBlur(50 * k)))
            d = ImageDraw.Draw(img)
            a = min(1.0, f / fps / 0.4)
            sz = int(W * 0.4 * (0.75 + 0.25 * a))
            for i, cx_ in ((0, W * 0.28), (1, W * 0.72)):
                img.alpha_composite(face(i).resize((sz, sz), Image.LANCZOS), (int(cx_ - sz / 2), int(H * 0.4 - sz / 2)))
                d.text((cx_, H * 0.4 + sz / 2 + 30 * k), names[i].split()[0].upper(), font=render.font(int(54 * k)),
                       anchor="ma", fill=mix(cols[i], 0.3), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
            d.text((W / 2, H * 0.1), "DRAW", font=render.font(int(140 * k)), anchor="ma", fill=(255, 255, 255),
                   stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
            d.text((W / 2, H * 0.4), "=", font=render.font(int(110 * k)), anchor="mm", fill=GOLD,
                   stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            if True:
                pop = 1 + 0.05 * math.sin(f / fps * 6)
                render.draw_rich(img, (W / 2, H * 0.7), "Who really won? Comment 👇",
                                 render.font(int(62 * k * pop)), (255, 255, 255), "ma", int(4 * k), (0, 0, 0))
            cta = (render.rcfg().get("end_cta") or "").strip()
            if cta:
                render.draw_rich(img, (W / 2, H * 0.86), cta, render.font(int(52 * k)),
                                 render.rcfg()["accent_color"], "ma", int(3 * k), (0, 0, 0))
            proc.stdin.write(img.convert("RGB").tobytes())
        for f in range(0 if draw else int(fps * END_S)):
            img = Image.new("RGBA", (W, H), mix(cols[win], 0.85, (10, 10, 18)) + (255,))
            d = ImageDraw.Draw(img)
            a = min(1.0, f / fps / 0.4)
            sz = int(W * 0.55 * (0.7 + 0.3 * a))
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).ellipse((W / 2 - sz * 0.62, H * 0.42 - sz * 0.62, W / 2 + sz * 0.62,
                                        H * 0.42 + sz * 0.62), fill=cols[win] + (170,))
            img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(60 * k)))
            img.alpha_composite(face(win).resize((sz, sz), Image.LANCZOS), (int(W / 2 - sz / 2), int(H * 0.42 - sz / 2)))
            d.text((W / 2, H * 0.1), "WINNER", font=render.font(int(120 * k)), anchor="ma", fill=cols[win],
                   stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            d.text((W / 2, H * 0.42 + sz / 2 + 40 * k), names[win].upper(), font=render.font(int(80 * k)),
                   anchor="ma", fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
            d.text((W / 2, H * 0.42 + sz / 2 + 140 * k), f"{final_share * 100:.0f}% of the domain",
                   font=render.font(int(48 * k)), anchor="ma", fill=(220, 225, 240))
            nxt = str(config.get()["slides"].get("domain", {}).get(
                "next_cta", "Who should fight next? Comment 👇")).strip()
            if nxt:                          # « prochain combat ? » : les gens commentent
                pop = 1 + 0.05 * math.sin(f / fps * 6)
                nf2 = render.font(int(62 * k * pop))
                while nf2.size > 24 and render.text_width(d, nxt, nf2) > W * 0.82:   # tient dans l'écran
                    nf2 = render.font(nf2.size - 2)
                render.draw_rich(img, (W / 2, H * 0.755), nxt, nf2, (255, 255, 255), "ma", int(4 * k), (0, 0, 0))
            cta = (render.rcfg().get("end_cta") or "").strip()
            if cta:
                render.draw_rich(img, (W / 2, H * 0.86), cta, render.font(int(52 * k)),
                                 render.rcfg()["accent_color"], "ma", int(3 * k), (0, 0, 0))
            proc.stdin.write(img.convert("RGB").tobytes())
        frames += int(fps * END_S)
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué")
    finally:
        if proc.poll() is None:
            proc.kill()
    import numpy as np
    dur = frames / fps
    n = int(dur * fusion.RATE) + fusion.RATE
    audio = np.zeros(n, dtype=np.float32)

    def vt(t):                                                   # temps simu → temps vidéo (cinématiques)
        return t + sum(dd for t0, dd in pauses if t0 <= t + 1e-6)

    def put(t, s, gain, video=False):
        i = int((t if video else vt(t)) * fusion.RATE)
        if 0 <= i < n:
            seg = s[: n - i]
            audio[i:i + len(seg)] += seg * gain
    tick = sfx("tick")
    low = tick[::2].repeat(2)[: len(tick)]
    last = [-1.0, -1.0]
    quiet = (director.clash, director.clash + 3.7) if not director.domain_clash else (-1, -1)
    for t, team in war.ticks:
        if quiet[0] <= t <= quiet[1]:                            # Beam Clash : pas de cliquetis par-dessus
            continue
        if t - last[team] >= 0.07:
            last[team] = t
            put(t, tick if team == 0 else low, 0.10)
    cache = {}
    count: dict = {}
    try:                                   # franchise du combat (sons officiels de la même série seulement)
        from . import seo
        fr = {(seo.anime_of(f["name"]) or ("",))[0].lower() for f in fighters}
        franchise = fr.pop() if len(fr) == 1 else None
    except Exception:
        franchise = None

    def S(fam, *a, variants=3):
        """Son d'une famille, avec 3 variantes qui tournent (pas le même coup à chaque fois)."""
        i = count.get((fam,) + a, 0)
        count[(fam,) + a] = i + 1
        key = (fam,) + a + (i % variants,)
        if key not in cache:
            cache[key] = sfx(fam, *a, mode=sounds, seed=i % variants, franchise=franchise)
        return cache[key]
    for t, team, slot, fx in director.events:
        fam = fx.get("sound", fx["fam"])
        if fam == "none" or (slot == "clash" and team == 1):
            continue
        if slot == "clash":
            fam = "clash"
        put(t, S(fam, names[team], slot, fx.get("name") if fam != "clash" else None),
            0.9 if slot in ("secret", "zone") else 0.6)
    for t, *_ in director.kos:                                   # K.O.
        put(t, S("ko"), 0.7)
    voices = []                                                  # répliques : ajoutées à la fin, le reste baisse dessous
    intro_snd = next((voice_file(sh["intro"]) for sh in sheets if sh.get("intro")), None)
    if intro_snd is not None:                                    # son d'ouverture (fiche « intro: », ex. « Yoooo »)
        voices.append((0.0, fusion.load_sound(intro_snd)))
    for h in intro_hit:                                          # accroche : choc au centre (sous le « yoooo »)
        put(h, S("hit"), 0.6 if intro_snd else 1.0, video=True)
        put(h, S("bomb"), 0.45 if intro_snd else 0.8, video=True)
    for t0, dd in finish_at:                                     # FINISH : coup final + grosse explosion
        put(vt(t0) - dd, S("ko"), 1.0, video=True)
        put(vt(t0) - dd + 0.05, S("bomb"), 1.0, video=True)
    voiced = set()
    for t, team, slot, fx in director.events:                    # réplique du perso à son secret (fiche « voice: »)
        if slot != "secret" or team in voiced or not sheets[team].get("voice"):
            continue
        v = voice_file(sheets[team]["voice"])
        if v is None:
            continue
        voiced.add(team)
        snd = fusion.load_sound(v)
        cine = [(t0, dd) for t0, dd in cine_at if abs(t0 - t) < 0.05]
        if cine:                                                 # pendant la cinématique (la simu est en pause)
            voices.append((vt(cine[0][0]) - cine[0][1] + 0.15, snd))
        else:
            voices.append((vt(t), snd))
    for t0, tm in eyes_at:                                       # cut-in des yeux : son du Sharingan (fiche
        es_name = sheets[tm].get("eyes_sound") or ("sharingan" if re.search(
            r"amaterasu|tsukuyomi|susano|kamui|kirin|sharingan|izanagi", " ".join(eye_moves[tm])) else None)
        es = voice_file(es_name) if es_name else None             # « eyes_sound: » ; Sharingan seulement pour l'Uchiwa
        if es is not None:
            voices.append((vt(t0 - 1e-4), fusion.load_sound(es)))
        else:
            put(vt(t0 - 1e-4), S("vanish"), 0.9, video=True)
    for t0, dd in cine_at:                                       # cinématique : montée en puissance (une fois)
        put(vt(t0) - dd, S("transform"), 1.0, video=True)
    lasth = -1.0
    for t, _ in war.hits:                                        # coups encaissés
        if t - lasth > 0.12:
            lasth = t
            put(t, S("hit", variants=5), 0.55)
    for t, _ in war.vanishes:
        put(t, S("vanish"), 0.6)
    for i_, t in enumerate(leap_land):                           # clones qui atterrissent : pouf + coup
        put(t, S("vanish") if i_ % 2 else S("hit", variants=5), 0.4)
    for t, *_ in war.subs:                                       # permutation : pouf
        put(t, S("vanish"), 0.6)
    lastm = -1.0
    for t, *_ in war.misses:
        if t - lastm > 0.3:
            lastm = t
            put(t, S("miss"), 0.3)
    for t, _ in stage_ev:                                        # formes intermédiaires
        put(t, S("powerup"), 0.7)
    for t, _ in director.sparks:
        put(t, S("teleport"), 0.5)
    put(win_at, sfx("win"), 0.9, video=True)                                 # gong de l'écran WINNER
    wav = out.with_suffix(".wav")
    from . import sfxdesign as _sd                               # mixage : aigus adoucis, niveau raisonnable
    audio = _sd.tame(audio, 6000, 0.4)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)                         # plus de saturation quand tout s'empile
    for t0, snd in voices:                                       # répliques bien audibles (« yoooo », « NARUTOOO »)
        i = int(t0 * fusion.RATE)
        if not (0 <= i < n):
            continue
        seg = snd[: n - i] / (float(np.abs(snd).max()) or 1.0) * 0.9
        L, f = len(seg), int(0.08 * fusion.RATE)
        duck = np.full(L, 0.35, dtype=np.float32)
        if L > 2 * f:
            duck[:f] = np.linspace(1, 0.35, f)
            duck[-f:] = np.linspace(0.35, 1, f)
        audio[i:i + L] = audio[i:i + L] * duck + seg
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1))
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"title": title, "episode": episode, "kind": "domain", "seed": seed, "scripted_winner": winner, "comeback": comeback, "sounds": sounds, "sfx_credits": _credits(), "seconds": round(dur, 1), "names": names,
            "winner": "Draw" if director.draw else names[win], "share": round(final_share, 3),
            "moves": [f"{names[tm]}: {fx['name']}" for _, tm, _, fx in director.events], "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    _brand_video(out)
    log.info("domain war : %s (%.0f %%) → %s", "égalité" if director.draw else names[win] + " gagne",
             final_share * 100, out.name)
    return out


def _brand_video(out):
    """Filigrane anti-vol sur les NOUVELLES vidéos (depuis le 02/11 ; config `slides.render.video_watermark`)."""
    from . import render as _r
    if _r.rcfg().get("video_watermark", True):
        try:
            _r.stamp_video(out)
        except Exception as e:  # pas de badge, ffmpeg… : la vidéo reste sans filigrane
            log.info("filigrane vidéo : %s", e)
