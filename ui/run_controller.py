"""Controlador da mini-run: mapa, duelo, draft e fim. Puro (sem pygame).

So chama a API publica de `core.run` (`new_run`, `choose_node`, `start_duel`,
`finish_duel`, `pick_draft`, `abandon`); nenhuma regra mora aqui. `IllegalAction` vira aviso.
O duelo e o `ui.controller.Controller` de sempre, iniciado com o duelo da `Run`.

Elementos clicaveis (`elem`):
    ("node", id)  ("abandon",)  ("draft_card", i)  ("draft_pick", i)
    ("continue",)  ("new_run",)  ("quit",)  ("quit_yes",)  ("quit_no",)
mais os do duelo (`("hand", i)`, `("slot", side, n)` ...), delegados ao `Controller`.
"""
from __future__ import annotations

from collections import Counter
from random import Random
from typing import Callable

import pygame

from core import Run, new_run
from core.duel import card_from_effect, card_from_special
from core.types import Card, Content, IllegalAction
from ui import audio, layout as L, layout_run as LR
from ui.controller import Controller, Toast

SCREENS = ("map", "duel", "draft", "finished")


class RunController:
    def __init__(self, content: Content, seed: int, *, ai_delay: float = 0.5,
                 seed_source: Callable[[], int] | None = None, run: Run | None = None) -> None:
        self.content = content
        self._given_run = run          # run pronta (ex.: deck da colecao) para a 1a partida
        self.ai_delay = ai_delay
        self.seed_source = seed_source or (lambda: Random().randrange(1, 10**6))
        self.new_game(seed)

    # ------------------------------------------------------------ ciclo
    def new_game(self, seed: int) -> None:
        self.seed = seed
        self.run = self._given_run or new_run(self.content, Random(seed))
        self._given_run = None
        self.duel_ctrl: Controller | None = None
        self.visited: list[str] = []          # ids dos nos escolhidos, em ordem
        self.draft_sel: int | None = None
        self.quit_confirm = False
        self.wants_quit = False
        self.toast: Toast | None = None
        self.last_pick: str | None = None
        self.draft_from: str = ""             # tipo do no que abriu o draft
        self.end_line: tuple[str, str] | None = None   # (pessoa, fala) no fim da run
        self.end_leader_id: str | None = None          # id do inimigo que falou (retrato)
        self.duels_started = 0
        self.abandoned = False

    def again(self) -> None:
        self.new_game(self.seed_source())

    @property
    def screen(self) -> str:
        return self.run.status if self.run.status in SCREENS else "map"

    def say(self, text: str, kind: str = "error", ttl: float = 2.5) -> None:
        self.toast = Toast(text, kind, ttl)
        if kind == "error":
            audio.sfx("ui_denied")

    # ------------------------------------------------------------ consultas (apresentacao)
    def enemy_of(self, node: dict) -> dict | None:
        return self.content.enemies.get(node.get("inimigo") or "")

    def node_title(self, node: dict) -> str:
        e = self.enemy_of(node)
        return e["nome"] if e else "Descanso"

    def node_rects(self) -> list[tuple[str, pygame.Rect]]:
        layers = self.run.layers
        out = []
        for li, layer in enumerate(layers):
            nodes = layer["nodes"]
            for ni, n in enumerate(nodes):
                out.append((n["id"], LR.node_rect(li, ni, len(nodes), len(layers))))
        return out

    def node_by_id(self, node_id: str) -> tuple[int, dict]:
        for li, layer in enumerate(self.run.layers):
            for n in layer["nodes"]:
                if n["id"] == node_id:
                    return li, n
        raise KeyError(node_id)

    def available_ids(self) -> list[str]:
        return [n["id"] for n in self.run.available_nodes()]

    def node_state(self, layer: int, node: dict) -> str:
        """done | lost | skipped | available | current | future."""
        r = self.run
        nid = node["id"]
        if layer < r.layer or r.status == "finished":
            if nid in self.visited:
                lost = (r.result == "derrota" and self.visited[-1] == nid
                        and layer == r.layer)
                return "lost" if lost else "done"
            return "skipped"
        if layer == r.layer:
            if r.status == "map":
                return "available"
            return "current" if r.node and r.node["id"] == nid else "skipped"
        return "future"

    def card_name(self, cid: str) -> str:
        table = self.content.specials if cid in self.content.specials else self.content.effects
        return table[cid]["nome"]

    def is_spirit(self, cid: str) -> bool:
        return cid in self.content.specials

    def deck_summary(self) -> dict:
        r = self.run
        eff = sum(1 for c in r.cards if not self.is_spirit(c))
        spi = len(r.cards) - eff
        return {"cats": len(r.cats), "effects": eff, "spirits": spi, "cards": len(r.cards),
                "total": r.deck_size()}

    def deck_summary_text(self) -> str:
        s = self.deck_summary()
        return f"{s['cats']} gatos, {s['effects']} efeitos, {s['spirits']} Espíritos"

    def deck_counts(self, spirits: bool) -> list[tuple[str, int]]:
        """[(nome, quantidade)] das cartas do draft (efeitos ou Espiritos), em ordem de entrada."""
        cnt = Counter(c for c in self.run.cards if self.is_spirit(c) == spirits)
        return [(self.card_name(c), n) for c, n in cnt.items()]

    def draft_cards(self) -> list[Card]:
        out = []
        for cid in self.run.draft_options:
            out.append(card_from_special(self.content, cid) if self.is_spirit(cid)
                       else card_from_effect(self.content, cid))
        return out

    def draft_owned(self, cid: str) -> int:
        return sum(1 for c in self.run.cards if c == cid)

    def draft_progress(self) -> str:
        """'1/2' nos drafts em sequencia (elite); vazio quando e um draft so."""
        total = self.run.draft_total
        return f"{self.run.draft_step}/{total}" if total > 1 else ""

    def draft_choose_text(self) -> str:
        return f"Escolha 1 de {len(self.run.draft_options)}"

    def draft_title(self) -> str:
        prog = self.draft_progress()
        extra = f" ({prog})" if prog else ""
        if self.draft_from == "descanso":
            return f"Descanso: {self.draft_choose_text().lower()}{extra}"
        return f"Vitória! {self.draft_choose_text()}{extra}"

    def draft_subtitle(self) -> str:
        node = self.run.node
        if self.draft_from == "descanso":
            return "O gato cochila e você revê o deck."
        return f"Você venceu {self.node_title(node)}." if node else ""

    def hint(self) -> str:
        if self.quit_confirm:
            return "ESC de novo cancela"
        if self.screen == "map":
            return "Clique num nó brilhante para seguir"
        if self.screen == "draft":
            return ("Clique em ESCOLHER (ou na carta de novo)" if self.draft_sel is not None
                    else "Clique numa carta para selecioná-la")
        return ""

    def path_lines(self) -> list[tuple[str, str]]:
        """[(texto, estado)] dos nos visitados, para o fim da run."""
        out = []
        for nid in self.visited:
            li, n = self.node_by_id(nid)
            txt = self.node_title(n) if n["tipo"] == "descanso" else f"{self.node_title(n)} ({n['tipo']})"
            out.append((txt, self.node_state(li, n)))
        return out

    def audio_context(self) -> str:
        """Contexto de musica (chave de data/audio.json) da tela atual da run."""
        s = self.screen
        if s == "duel":
            return "duelo_chefe" if self.run.node and self.run.node.get("tipo") == "chefe" else "duelo"
        if s == "finished":
            return "fim_vitoria" if self.run.result == "vitoria" else "fim_derrota"
        return "mapa"

    # ------------------------------------------------------------ entrada
    def hit(self, pos: tuple[int, int]) -> tuple | None:
        if self.screen == "duel" and self.duel_ctrl is not None:
            if self.quit_confirm:
                return LR.hit_test(pos, "duel", confirm=True)
            return self.duel_hit(pos)
        return LR.hit_test(pos, self.screen,
                           nodes=self.node_rects() if self.screen == "map" else None,
                           n_draft=len(self.run.draft_options), selected=self.draft_sel,
                           confirm=self.quit_confirm)

    def duel_hit(self, pos: tuple[int, int]) -> tuple | None:
        c = self.duel_ctrl
        if c.final_visible:
            return ("continue",) if L.continue_rect().collidepoint(pos) else None
        return L.hit_test(pos, len(c.shown.me.hand), confirm=c.confirming)

    def click(self, elem: tuple | None) -> None:
        if self.quit_confirm:
            if elem == ("quit_yes",):
                self.quit_confirm = False
                audio.sfx("ui_click")
                self.abandon()
            elif elem == ("quit_no",):
                self.quit_confirm = False
                audio.sfx("ui_back")
            return
        if elem is None:
            if self.screen == "duel" and self.duel_ctrl:
                self.duel_ctrl.click(None)
            elif self.screen == "draft":
                self.draft_sel = None
            return
        kind = elem[0]
        try:
            if kind == "node" and self.screen == "map":
                self.choose(elem[1])
            elif kind == "abandon" and self.screen == "map":
                self.quit_confirm = True
                audio.sfx("ui_open_modal")
            elif kind == "draft_card" and self.screen == "draft":
                self.click_draft(elem[1])
            elif kind == "draft_pick" and self.screen == "draft":
                self.pick(elem[1])
            elif kind == "continue" and self.screen == "duel":
                audio.sfx("ui_click")
                self.continue_duel()
            elif kind == "new_run" and self.screen == "finished":
                audio.sfx("ui_click")
                self.again()
            elif kind == "quit" and self.screen == "finished":
                audio.sfx("ui_back")
                self.wants_quit = True
            elif self.screen == "duel" and self.duel_ctrl:
                self.duel_ctrl.click(elem)
        except IllegalAction as e:
            self.say(str(e))

    def cancel(self) -> None:
        """ESC / botao direito: cancela a etapa atual; sem nada a cancelar pede para abandonar."""
        if self.quit_confirm:
            self.quit_confirm = False
            audio.sfx("ui_back")
            return
        s = self.screen
        if s == "draft":
            self.draft_sel = None
        elif s == "map":
            self.quit_confirm = True
            audio.sfx("ui_open_modal")
        elif s == "duel" and self.duel_ctrl:
            c = self.duel_ctrl
            if c.phase in ("over", "dice"):
                return
            if c.sel is not None or c.confirming:
                c.cancel()
            else:
                self.quit_confirm = True
                audio.sfx("ui_open_modal")
        elif s == "finished":
            self.wants_quit = True

    def confirm_key(self) -> None:
        """ENTER: continuar (fim do duelo), escolher a carta selecionada, nova run."""
        s = self.screen
        try:
            if s == "duel" and self.duel_ctrl and self.duel_ctrl.final_visible:
                self.continue_duel()
            elif s == "draft" and self.draft_sel is not None:
                self.pick(self.draft_sel)
            elif s == "finished":
                self.again()
        except IllegalAction as e:
            self.say(str(e))

    # ------------------------------------------------------------ transicoes
    def choose(self, node_id: str) -> None:
        self.run.choose_node(node_id)
        self.visited.append(node_id)
        node = self.run.node
        audio.sfx("rest" if node and node["tipo"] == "descanso" else "node_select")
        if node and node["tipo"] == "descanso":
            self.draft_from = "descanso"
            self.draft_sel = None
        if self.run.status == "duel":
            self.start_duel()
        elif self.run.status == "finished":
            self._on_finished()

    def start_duel(self) -> None:
        self.duels_started += 1
        dseed = self.seed * 1000 + self.duels_started
        duel = self.run.start_duel(Random(dseed))
        self.duel_ctrl = Controller(self.content, dseed, ai_delay=self.ai_delay,
                                    enemy_id=self.run.node["inimigo"], duel=duel)

    def continue_duel(self) -> None:
        c = self.duel_ctrl
        if c is None or not c.final_visible:
            return
        node_type = self.run.node["tipo"] if self.run.node else ""
        won = c.duel.winner == "player"
        line, who = c.final_line, c.enemy_name()
        leader_id = c.enemy_id
        self.run.finish_duel(c.duel)
        self.duel_ctrl = None
        if self.run.status == "draft":
            self.draft_from = node_type
            self.draft_sel = None
        elif self.run.status == "finished":
            if line and (not won or node_type == "chefe"):
                self.end_line = (who, line)
                self.end_leader_id = leader_id
            self._on_finished()

    def click_draft(self, i: int) -> None:
        if not 0 <= i < len(self.run.draft_options):
            return
        if self.draft_sel == i:
            self.pick(i)
        else:
            self.draft_sel = i
            audio.sfx("ui_click")

    def pick(self, i: int) -> None:
        self.last_pick = self.run.pick_draft(i)
        audio.sfx("draft_pick")
        self.draft_sel = None
        if self.run.status == "finished":
            self._on_finished()

    def abandon(self) -> None:
        if self.run.status != "finished":
            self.run.abandon()
            self.abandoned = True
        self.duel_ctrl = None
        self._on_finished()

    def _on_finished(self) -> None:
        self.quit_confirm = False
        self.draft_sel = None

    # ------------------------------------------------------------ tempo
    def update(self, dt: float) -> None:
        if self.toast:
            self.toast.ttl -= dt
            if self.toast.ttl <= 0:
                self.toast = None
        if self.screen == "duel" and self.duel_ctrl and not self.quit_confirm:
            self.duel_ctrl.update(dt)
