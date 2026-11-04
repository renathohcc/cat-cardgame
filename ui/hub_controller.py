"""Controlador do hub: menu inicial, colecao, run e resultado. Puro (sem pygame).

So chama a API publica do core (`new_game`, `read_save`, `write_save`) e delega a colecao ao
`CollectionController` e a run ao `RunController`. O save so e gravado entre runs: nada de
retomar run (fechar a janela no meio da run = run perdida, o save fica como estava).

Modos: "menu" | "cercado" (hub: Criatorio animado) | "colecao" | "criatorio" (breed) | "run" |
"novidades" | "adocao" | "resultado". Tudo que termina (adocao, resultado, colecao) volta ao cercado.
Elementos do menu: ("menu", "continue"|"new_game"|"quit") ("confirm_yes",) ("confirm_no",)
Resultado: ("result_back",)
"""
from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from random import Random

from dataclasses import dataclass

from core import (RunSettlement, SaveData, advance_after_run, close_run, create_adoption, has_pending_adoption,
                  kittens_in_basket, new_game, prestige_level, read_save, update_prestige, write_save)
from core import Content, breed_cfg
from core.types import IllegalAction
from ui import audio, errors, layout_hub as LH, timing as timing_mod
from ui.adoption_controller import AdoptionController
from ui.breed_controller import BreedController, NewsController
from ui.collection_controller import CollectionController
from ui.controller import Toast
from ui import layout_pen as LP, layout_shop as LS, pen_world
from ui.render_lock import UnlockFx, update_fx
from ui.shop_controller import ShopController
from ui.pen_controller import PenController, PenEntry
from ui.pen_geometry import load_geometry, pen_limits
from ui.run_controller import RunController

SHORT_RUN_TEXT = "Run curta: não conta para o breed"
DEFAULT_SAVE = Path(__file__).resolve().parent.parent / "saves" / "save.json"


@dataclass
class RunSummary:
    """Resumo do fim da run (do `close_run` do core): ganhos por fonte, meta e Prestigio."""
    settlement: RunSettlement
    win: bool
    nodes: int
    age: float = 0.0                   # tempo na tela (anima a barra de meta)

    @property
    def prestige_up(self) -> bool:
        return self.settlement.prestige_up


class HubController:
    def __init__(self, content: Content, save_path: Path | str | None, seed: int, *,
                 ai_delay: float = 0.5, clock: Callable[[], datetime] | None = None) -> None:
        self.content = content
        self.clock = clock                        # relogio do ciclo do dia (None = meio-dia fixo; o jogo passa datetime.now)
        self.save_path = Path(save_path) if save_path is not None else None   # None = so memoria
        self.seed = seed
        self.ai_delay = ai_delay
        self.mode = "menu"
        self.save: SaveData | None = None
        self.col: CollectionController | None = None
        self.rc: RunController | None = None
        self.adopt: AdoptionController | None = None
        self.breed: BreedController | None = None
        self.news: NewsController | None = None
        self.short_run = False                    # ultima run nao contou para o breed
        self.load_error: str | None = None        # texto do erro quando o save esta corrompido
        self.has_file = False
        self.confirm_new = False
        self.wants_quit = False
        self.toast: Toast | None = None
        self.result_text = ""
        self.result_win = False
        self.result_detail: list[str] = []
        self.runs_started = 0
        self.pen: PenController | None = None
        self.ficha: str | None = None             # gato com a ficha aberta no cercado
        self.breed_from = "cercado"               # para onde o BREED volta
        self._pen_sync_clock = 0.0
        self.end_jingle = False                   # run acabou: toca o jingle ate o 1o clique
        self.options_requested = False            # menu > OPCOES: o loop abre a tela de opcoes
        self.shop: ShopController | None = None   # loja e compras (areas, racoes, decoracao)
        self.area_open: str | None = None         # painel de compra de uma area aberto no cercado
        self.unlock_fx: list[UnlockFx] = []       # areas recem-compradas (animacao)
        self.lock_spec = pen_world.load_lock_spec()
        self.area_content = pen_world.load_content_spec()      # arte das areas 4 a 6 (so desenha depois de aberta)
        self.summary: RunSummary | None = None    # resumo da ultima run (tela de resultado)
        self.unsettled: tuple | None = None       # run cujo close_run falhou (tenta de novo ao voltar ao cercado)
        self.summary_pending = False              # falta mostrar o resumo antes de voltar ao cercado
        self.prestige_seen: int | None = None
        self.seal: list | None = None             # [nivel, idade] do selo de Prestigio
        self.hud_flash = 0.0                      # realce das vagas depois de comprar uma area
        self.reload()

    # ------------------------------------------------------------ save
    def reload(self) -> None:
        """Le o save do disco. Qualquer falha de leitura vira aviso (nunca derruba o jogo)."""
        self.save, self.load_error, self.has_file = None, None, False
        if self.save_path is None or not self.save_path.exists():
            return
        self.has_file = True
        try:
            self.save = read_save(self.save_path, self.content)
        except Exception as e:  # noqa: BLE001 - arquivo ilegivel/invalido: so avisar
            errors.log_exception(e, "read_save")
            self.load_error = str(e) or type(e).__name__

    def persist(self) -> str | None:
        """Grava o save; devolve texto de erro (ou None). Sem caminho = nao grava."""
        if self.save is None or self.save_path is None:
            return None
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            warn = write_save(self.save, self.save_path)
        except Exception as e:  # noqa: BLE001 - qualquer falha vira aviso, nunca derruba o jogo
            errors.log_exception(e, "persist")
            return str(e) or type(e).__name__
        self.has_file = True
        if warn:                       # o save foi gravado, mas a copia do v1 falhou: avisa e registra
            errors.log_exception(RuntimeError(str(warn)), "persist: backup do save v1")
            self.say("Não consegui guardar a cópia (backup) do save antigo.", "warn", 5.0)
        return None

    def adopt_save(self, save: SaveData) -> None:
        self.save = save
        self.load_error = None
        self.prestige_seen = None
        self.shop, self.area_open, self.unlock_fx = None, None, []
        self.col = CollectionController(self.content, save, self.persist)

    # ------------------------------------------------------------ consultas
    @property
    def screen(self) -> str:
        return self.mode

    @property
    def can_continue(self) -> bool:
        return self.save is not None and self.load_error is None

    def menu_enabled(self) -> dict[str, bool]:
        return {"continue": self.can_continue, "new_game": True, "quit": True}

    def menu_labels(self) -> list[tuple[str, str, bool]]:
        en = self.menu_enabled()
        names = {"continue": "CONTINUAR", "new_game": "NOVO JOGO", "quit": "SAIR"}
        return [(k, names[k], en[k]) for k in LH.MENU_ITEMS]

    def save_summary(self) -> str:
        if self.can_continue:
            s = self.save
            txt = f"Save: {len(s.cats)} gatos, deck {len(s.deck)}/{self.content.rules['duel']['deck_size']}"
            return txt + ("  (adoção pendente)" if has_pending_adoption(s) else "")
        if self.load_error:
            return "Save corrompido ou ilegível."
        return "Nenhum save encontrado."

    def say(self, text: str, kind: str = "error", ttl: float = 2.5) -> None:
        self.toast = Toast(text, kind, ttl)
        if kind == "error":
            audio.sfx("ui_denied")

    # ------------------------------------------------------------ cercado
    def pen_max(self) -> int:
        return pen_limits(self.content.rules)[0]

    def pen_zone_caps(self) -> dict[str, int]:
        return pen_limits(self.content.rules)[1]

    def pen_geo(self):
        return self.pen.geo if self.pen else load_geometry()

    def enter_pen(self) -> None:
        """Abre o cercado (cria o controlador na primeira vez) e sincroniza o elenco."""
        self.retry_settle()
        if self.col is None and self.save is not None:
            self.col = CollectionController(self.content, self.save, self.persist)
        if self.pen is None:
            self.pen = PenController(Random(self.seed * 31 + 7), load_geometry(), self.pen_max(), self.clock,
                                 self.pen_zone_caps(), audio_rng=Random(self.seed * 53 + 11))
        self.ficha = None
        self.area_open = None
        self.summary_pending = False
        self.pen.hold(None)
        if self.shop is None or self.shop.save is not self.save:
            self.shop = ShopController(self.content, self.save, self.persist, self.refresh_world, self._area_unlocked)
        if not any(o.gate for o in self.pen.objects):
            for deco_id, (kind, x, y) in pen_world.DECOR_ANCHORS.items():
                self.pen.add_decor(deco_id, kind, x, y)
        if self.prestige_seen is None:
            self.prestige_seen = prestige_level(self.content, self.save)
        self.mode = "cercado"
        self.refresh_world()

    def refresh_world(self) -> None:
        """Liga ao quintal o que o save diz: areas ainda bloqueadas e decoracao comprada."""
        if self.pen is None or self.save is None:
            return
        locks = pen_world.locked_rects(self.lock_spec, set(self.save.areas_unlocked))
        opened = {a for a in self.area_content if a in set(self.save.areas_unlocked)}
        self.pen.set_world(locks, set(self.save.decorations_owned), self.area_content, opened)
        self.sync_pen()

    def _area_unlocked(self, area_id: str) -> None:
        """Area comprada: anima o desbloqueio, toca o som e realca as vagas."""
        self.unlock_fx.append(UnlockFx(area_id))
        self.hud_flash = timing_mod.current().economy.hud_flash
        audio.sfx("level_up")

    @property
    def basket_count(self) -> int:
        """Filhotes na cesta (antes do cercadinho de filhotes): a regra e do core."""
        if self.save is None or not kittens_in_basket(self.content, self.save):
            return 0
        return sum(1 for c in self.save.cats if c.stage == "kitten")

    def _check_prestige(self) -> None:
        """Nivel de Prestigio subiu (corrida, adocao, compra): mostra o selo e toca o som."""
        if self.save is None or self.prestige_seen is None:
            return
        lvl = prestige_level(self.content, self.save)
        if lvl > self.prestige_seen:
            update_prestige(self.content, self.save)
            self.persist()
            self.seal = [lvl, 0.0]
            audio.sfx("level_up")
        self.prestige_seen = max(self.prestige_seen, lvl)

    def pen_entries(self) -> list[PenEntry]:
        out: list[PenEntry] = []
        if self.save is None or self.col is None:
            return out
        partner: dict[str, str] = {}
        for b in self.save.breeding:
            partner[b["male"]], partner[b["female"]] = b["female"], b["male"]
        for c in self.save.cats:
            st = self.col.state_of(c)
            tag = {"filhote": "filhote", "breed": "breed", "deck": "deck"}.get(st, "livre")
            out.append(PenEntry(c.id, c.breed, c.stage == "kitten", tag, partner.get(c.id)))
        return out

    def sync_pen(self) -> None:
        if self.pen is not None:
            self.pen.sync(self.pen_entries())
            if self.ficha and not self._cat_exists(self.ficha):
                self.close_ficha()

    def _cat_exists(self, cat_id: str) -> bool:
        return self.save is not None and any(c.id == cat_id for c in self.save.cats)

    def open_ficha(self, cat_id: str) -> None:
        self.ficha = cat_id
        self.col.selected = cat_id
        self.pen.poke(cat_id)
        self.pen.hold(cat_id)

    def close_ficha(self) -> None:
        self.ficha = None
        if self.pen:
            self.pen.hold(None)

    def ficha_rect(self):
        c = self.pen.cat(self.ficha) if self.pen and self.ficha else None
        return LP.ficha_rect(c.x if c else 0, self.pen_geo())

    def pen_buttons(self) -> tuple[str, ...]:
        return tuple(b for b in LP.BUTTONS if b != "adocao" or self.adoption_pending)

    @property
    def adoption_pending(self) -> bool:
        return self.save is not None and has_pending_adoption(self.save)

    def pen_label(self, cat_id: str) -> str:
        """Nome mostrado ao passar o mouse: apelido ou raca."""
        cat = next((c for c in self.save.cats if c.id == cat_id), None) if self.save else None
        return "" if cat is None else (cat.name or self.col.breed_name(cat))

    def _modal_open(self) -> bool:
        return self.col is not None and (self.col.editing or self.col.confirm_donate)

    # ------------------------------------------------------------ entrada
    def hit(self, pos: tuple[int, int]) -> tuple | None:
        m = self.mode
        if m == "run":
            return self.rc.hit(pos) if self.rc else None
        if m == "menu":
            return LH.hit_test(pos, m, confirm=self.confirm_new)
        if m == "colecao":
            return self.col.hit(pos)
        if m == "cercado":
            return self._hit_pen(pos)
        if m == "adocao":
            return self.adopt.hit(pos)
        if m == "criatorio":
            return self.breed.hit(pos)
        if m == "novidades":
            return self.news.hit(pos)
        if m == "loja":
            return self.shop.hit(pos)
        return LH.hit_test(pos, m)

    def _hit_pen(self, pos: tuple[int, int]) -> tuple | None:
        if self.area_open:
            return LS.area_panel_hit(pos, self.area_open)
        if self._modal_open():
            return LH.hit_test(pos, "colecao", rename=self.col.editing, donate=self.col.confirm_donate)
        if self.ficha:
            e = LP.ficha_hit(pos, self.ficha_rect())
            if e:
                return e
        e = LP.panel_hit(pos, self.pen_buttons(), self.pen_geo())
        if e:
            return e
        sign = self.sign_at(pos)
        if sign:
            return ("area_sign", sign)
        cid = self.pen.hit(pos) if self.pen else None
        if cid:
            return ("pen_cat", cid)
        oi = self.pen.hit_object(pos) if self.pen else None
        if oi is not None:
            return ("pen_obj", oi)
        return ("pen_floor",) if LP.area_rect(self.pen_geo()).collidepoint(pos) else None

    def sign_at(self, pos: tuple[int, int]) -> str | None:
        """Id da area cuja placa esta sob `pos` (so areas ainda nao compradas)."""
        if self.save is None:
            return None
        for a in self.lock_spec.areas:
            if a.id in self.save.areas_unlocked:
                continue
            x, y, w, h = pen_world.sign_rect(a, self.lock_spec.sign_size)
            if x <= pos[0] < x + w and y <= pos[1] < y + h + 22:       # +22: o mini-selo sob a placa
                return a.id
        return None

    def _click_area(self, elem: tuple | None) -> None:
        """Painel da area aberto: COMPRAR, FECHAR; clicar fora tambem fecha."""
        if elem is not None and elem[0] == "area_panel":
            return
        if elem is not None and elem[0] == "area_buy":
            if self.shop.buy_area(elem[1]):
                self.area_open = None
            return
        self.area_open = None

    def _click_pen(self, elem: tuple | None) -> None:
        if self.area_open:
            self._click_area(elem)
            return
        if elem is None:
            return
        col, kind = self.col, elem[0]
        if self._modal_open():
            col.click(elem)
            self.sync_pen()
            return
        if kind == "pen_cat":
            self.open_ficha(elem[1])
        elif kind == "pen_obj":
            self.close_ficha()
            self.pen.poke_object(elem[1])
        elif kind in ("pen_floor", "ficha_close"):
            self.close_ficha()
        elif kind == "ficha_rename":
            col.selected = self.ficha
            col.click(("rename",))
        elif kind == "ficha_donate":
            col.selected = self.ficha
            col.click(("donate",))
        elif kind == "area_sign":
            self.close_ficha()
            self.area_open = elem[1]
        elif kind == "pen_btn":
            self._pen_button(elem[1])

    def _pen_button(self, name: str) -> None:
        if name == "start":
            if self.col.can_start:
                self.start_run()
            else:
                self.col.click(("start",))
        elif name == "colecao":
            self.close_ficha()
            self.col.refresh_deck()
            self.mode = "colecao"
        elif name == "adocao":
            self.close_ficha()
            self.open_pending_adoption()
        elif name == "breed":
            self.close_ficha()
            self.breed_from = "cercado"
            self.open_breed()
        elif name == "loja":
            self.close_ficha()
            self.mode = "loja"
        elif name == "menu":
            self.close_ficha()
            self.mode = "menu"

    # ------------------------------------------------------------ audio
    BACK_KINDS = ("back", "result_back", "ficha_close", "confirm_no", "donate_no", "rename_cancel", "shop_back",
                  "area_close")
    QUIET_KINDS = ("none", "pen_obj", "row", "scroll", "area_panel")

    def _snap(self) -> tuple:
        s = self.save
        return (audio.manager().total_requests, s.coins if s else 0, len(s.cats) if s else 0,
                len(s.breeding) if s else 0, self.mode, self._modal_flags(), id(s))

    def _modal_flags(self) -> tuple:
        col = self.col
        return (self.confirm_new, bool(col and col.editing), bool(col and col.confirm_donate),
                self.ficha is not None, self.area_open is not None)

    def _sound_after(self, elem: tuple | None, before: tuple, key: bool = False) -> None:
        """Som de uma acao de meta, derivado do que mudou (nunca decide regra)."""
        mgr, s = audio.manager(), self.save
        if mgr.total_requests != before[0]:
            return                                          # ja tocou algo (ex.: ui_denied, pet)
        same = s is not None and id(s) == before[6]
        if same and s.coins > before[1]:
            audio.sfx("coin")
        elif same and len(s.cats) > before[2]:
            audio.sfx("adopt")
        elif same and len(s.breeding) > before[3]:
            audio.sfx("breed_start")
        else:
            flags = self._modal_flags()
            opened = any(n and not o for n, o in zip(flags[:3], before[5][:3]))
            closed = any(o and not n for n, o in zip(flags, before[5]))
            if opened:
                audio.sfx("ui_open_modal")
            elif (elem and elem[0] in self.BACK_KINDS) or (key and (closed or self.mode != before[4])):
                audio.sfx("ui_back")
            elif elem and not key and elem[0] not in self.QUIET_KINDS:
                audio.sfx("ui_click")

    def _drain_pen_sounds(self) -> None:
        if not self.pen:
            return
        sounds, self.pen.sounds = self.pen.sounds, []
        if self.mode == "cercado":
            for cue in sounds:
                audio.sfx(cue)

    def audio_context(self) -> str:
        """Contexto de musica (chave de data/audio.json) da tela atual."""
        m = self.mode
        if m == "run" and self.rc:
            return self.rc.audio_context()
        if self.end_jingle and m in ("novidades", "adocao", "resultado"):
            return "fim_vitoria" if self.result_win else "fim_derrota"
        if m == "cercado":
            night = self.pen is not None and self.pen.day.dominant in ("entardecer", "noite")
            return "criatorio_noite" if night else "criatorio_dia"
        return {"colecao": "colecao", "loja": "colecao", "criatorio": "breed", "novidades": "breed", "adocao": "adocao",
                "resultado": "fim_vitoria" if self.result_win else "fim_derrota"}.get(m, "menu")

    def click(self, elem: tuple | None) -> None:
        if self.mode == "run":
            self._click(elem)
            return
        before = self._snap()
        self.end_jingle = False
        self._click(elem)
        self._drain_pen_sounds()
        self._sound_after(elem, before)
        self._check_prestige()

    def _click(self, elem: tuple | None) -> None:
        m = self.mode
        if m == "run" and self.rc:
            self.rc.click(elem)
            self._check_run_end()
        elif m == "menu":
            self._click_menu(elem)
        elif m == "cercado":
            self._click_pen(elem)
        elif m == "loja":
            self._click_shop(elem)
        elif m == "colecao":
            act = self.col.click(elem)
            if act == "back":
                self.enter_pen()
            elif act == "start":
                self.start_run()
            elif act == "breed":
                self.breed_from = "colecao"
                self.open_breed()
        elif m == "criatorio":
            if self.breed.click(elem) == "back":
                self.close_breed()
        elif m == "novidades":
            if self.news.click(elem) == "done":
                self._finish_news()
        elif m == "adocao":
            if self.adopt.click(elem) == "done":
                self._finish_adoption()
        elif m == "resultado" and elem == ("result_back",):
            self.enter_pen()

    def _click_shop(self, elem: tuple | None) -> None:
        coins = self.save.coins
        act = self.shop.click(elem)
        if act == "back":
            self.enter_pen()
        elif isinstance(act, tuple) and act[0] == "goto_area":
            self.enter_pen()
            self.area_open = act[1]
        elif self.save.coins < coins:
            audio.sfx("coin")

    def _click_menu(self, elem: tuple | None) -> None:
        if self.confirm_new:
            if elem == ("confirm_yes",):
                self.confirm_new = False
                self.start_new_game()
            elif elem == ("confirm_no",):
                self.confirm_new = False
            return
        if elem and elem[0] in ("vol", "vol_set", "mute"):
            mgr = audio.manager()
            if elem[0] == "mute":
                mgr.toggle_mute()
            elif elem[0] == "vol":
                mgr.adjust_volume(elem[1], elem[2])
            else:
                mgr.set_volume(elem[1], elem[2])
            audio.sfx("ui_click")
            return
        if elem == ("menu_options",):
            self.options_requested = True
            return
        if not elem or elem[0] != "menu":
            return
        item = elem[1]
        if item == "continue" and self.can_continue:
            self.col = CollectionController(self.content, self.save, self.persist)
            self.enter_pen()
        elif item == "new_game":
            if self.has_file:
                self.confirm_new = True
            else:
                self.start_new_game()
        elif item == "quit":
            self.wants_quit = True

    def backup_save(self) -> str | None:
        """Move o save atual para `<nome>.bak` (substitui .bak anterior). Devolve erro ou None."""
        p = self.save_path
        if p is None or not p.exists():
            return None
        try:
            os.replace(p, p.with_name(p.name + ".bak"))
        except Exception as e:  # noqa: BLE001 - falha de backup nao impede o jogo novo
            return str(e) or type(e).__name__
        return None

    def open_pending_adoption(self) -> bool:
        """Se o save tem oferta pendente, abre a tela de Adocao. Devolve se abriu."""
        if self.save is None or not has_pending_adoption(self.save):
            return False
        self.adopt = AdoptionController(self.content, self.save, self.persist)
        self.adopt.note = SHORT_RUN_TEXT if self.short_run else ""
        self.mode = "adocao"
        return True

    def open_breed(self) -> None:
        self.breed = BreedController(self.content, self.save, self.persist)
        self.mode = "criatorio"

    def close_breed(self) -> None:
        self.breed = None
        self.col.refresh_deck()          # pais em breed saem do rascunho do deck
        if self.breed_from == "colecao":
            self.mode = "colecao"
        else:
            self.enter_pen()

    def _finish_news(self) -> None:
        self.news = None
        if self.open_pending_adoption():
            return
        self.mode = "resultado"

    def _finish_adoption(self) -> None:
        toast = self.adopt.toast if self.adopt else None
        self.adopt = None
        if self.col is None:
            self.col = CollectionController(self.content, self.save, self.persist)
        self.col.toast = toast
        rows = self.col.rows()
        if self.col.selected_cat() is None and rows:
            self.col.selected = rows[0].cat.id
        if self.summary_pending and self.summary is not None:
            self.mode = "resultado"          # depois da adocao, o resumo da run (moedas, meta, Prestigio)
            return
        self.enter_pen()

    def start_new_game(self) -> None:
        bak_err = self.backup_save()
        self.adopt_save(new_game(self.content, Random(self.seed)))
        err = self.persist()
        self.enter_pen()
        if err:
            self.col.say(f"Não consegui salvar: {err}")
        elif bak_err:
            self.col.say(f"Aviso: backup do save antigo falhou: {bak_err}")

    def start_run(self) -> None:
        self.runs_started += 1
        run_seed = self.seed + self.runs_started
        run = self.col.start_run(Random(run_seed))
        self.rc = RunController(self.content, run_seed, ai_delay=self.ai_delay, run=run)
        self.mode = "run"

    def key_escape(self) -> None:
        if self.mode == "run":
            self._key_escape()
            return
        before = self._snap()
        self._key_escape()
        self._sound_after(None, before, key=True)

    def _key_escape(self) -> None:
        m = self.mode
        if m == "menu":
            self.confirm_new = False
        elif m == "colecao":
            if self.col.editing:
                self.col.cancel_rename()
            elif self.col.confirm_donate:
                self.col.confirm_donate = False
            else:
                self.enter_pen()
        elif m == "loja":
            self.enter_pen()
        elif m == "cercado":
            if self.area_open:
                self.area_open = None
            elif self.col.editing:
                self.col.cancel_rename()
            elif self.col.confirm_donate:
                self.col.confirm_donate = False
            elif self.ficha:
                self.close_ficha()
            else:
                self.mode = "menu"
        elif m == "run" and self.rc:
            self.rc.cancel()
            self._check_run_end()
        elif m == "criatorio":
            self.close_breed()
        elif m == "novidades":
            self._finish_news()
        elif m == "adocao":
            if self.adopt.room_for:      # painel de gatil cheio aberto: ESC so fecha o painel
                self.adopt.close_room()
                return
            self.adopt = None            # a oferta fica no save; o botao ADOCAO do cercado reabre
            self.enter_pen()
        elif m == "resultado":
            self.enter_pen()

    def escape(self) -> bool:
        """ESC do jogo: faz o que o ESC ja fazia (cancelar, fechar, voltar). False = nada a
        cancelar no cercado/mapa/duelo/draft: a UI abre o menu de pausa."""
        if self.mode == "run" and self.rc:
            ok = self.rc.escape()
            self._check_run_end()
            return ok
        if self.mode == "cercado":
            col = self.col
            if not (col.editing or col.confirm_donate or self.ficha or self.area_open):
                return False
        self.key_escape()
        return True

    def go_menu(self) -> None:
        """Pausa > SAIR PARA O MENU (so no cercado; o save ja foi gravado)."""
        if self.mode == "cercado":
            self.close_ficha()
            self.area_open = None
            self.mode = "menu"

    def scene_key(self) -> str:
        return f"run_{self.rc.screen}" if self.mode == "run" and self.rc else self.mode

    def key_enter(self) -> None:
        m = self.mode
        if m in ("colecao", "cercado"):
            if self.col.editing:
                self.col.confirm_rename()
        elif m == "run" and self.rc:
            self.rc.confirm_key()
            self._check_run_end()
        elif m == "novidades":
            self._finish_news()
        elif m == "resultado":
            self.enter_pen()

    def text_input(self, text: str) -> None:
        if self.mode in ("colecao", "cercado"):
            self.col.type_text(text)

    def backspace(self) -> None:
        if self.mode in ("colecao", "cercado"):
            self.col.backspace()

    def scroll(self, n: int) -> None:
        if self.mode == "adocao":
            self.adopt.scroll_by(n)
        if self.mode == "criatorio":
            self.breed.scroll_by("M", n)
            self.breed.scroll_by("F", n)
        if self.mode == "colecao" and not self.col.editing:
            self.col.scroll_by(n)

    @property
    def editing_text(self) -> bool:
        return self.mode in ("colecao", "cercado") and self.col is not None and self.col.editing

    # ------------------------------------------------------------ fim da run
    def _check_run_end(self) -> None:
        rc = self.rc
        if self.mode != "run" or rc is None or rc.screen != "finished":
            return
        win = rc.run.result == "vitoria"
        n = rc.run.nodes_cleared
        self.result_win = win
        self.result_text = f"Run encerrada: {'vitória' if win else 'derrota'}, nós vencidos {n}"
        self.result_detail = []
        self.short_run = n < breed_cfg(self.content)["min_nodes_for_run_count"]
        if rc.abandoned:
            self.result_detail.append("Você abandonou a run (conta como derrota).")
        elif rc.end_line:
            self.result_detail.append(f"{rc.end_line[0]}: \"{rc.end_line[1]}\"")
        result = "abandono" if rc.abandoned else rc.run.result
        run = rc.run
        self.rc = None
        self.summary = self._settle(run, win, n)         # moedas, historico e Prestigio (core)
        self.summary_pending = self.summary is not None
        # ordem fixa: breed/crescimento -> adocao -> UM unico write_save
        aftermath = advance_after_run(self.content, self.save,
                                      Random(self.seed * 104729 + self.runs_started), n)
        try:
            create_adoption(self.content, self.save, Random(self.seed * 7919 + self.runs_started),
                            result, n)
        except IllegalAction as e:      # ja havia oferta pendente: mantem a antiga
            self.say(str(e))
        err = self.persist()            # UM unico write_save
        if err:
            self.say(f"Não consegui salvar: {err}")
        self._check_prestige()
        self.end_jingle = True
        if aftermath.born:
            audio.sfx("kitten_born")
        elif aftermath.grown:
            audio.sfx("level_up")
        if aftermath.born or aftermath.grown:
            self.news = NewsController(self.content, self.save, aftermath)
            self.mode = "novidades"
            return
        if self.open_pending_adoption():
            return
        self.result_detail.append("Nenhum gato para adotar desta vez")
        self.mode = "resultado"

    def _settle(self, run, win: bool, nodes: int) -> RunSummary | None:
        """`close_run` do core. Run que nao e uma `Run` de verdade (teste/demo) fica sem resumo."""
        try:
            summary = RunSummary(close_run(self.content, self.save, run), win, nodes)
        except IllegalAction as e:                       # erro de regra esperado (ex.: run ja fechada)
            self.say(str(e))
            return None
        except Exception as e:  # noqa: BLE001 - bug: nao perder moedas/historico/Prestigio da run
            errors.log_exception(e, "close_run")
            self.unsettled = (run, win, nodes)           # mantem a run pendente para tentar de novo
            self.result_detail.append("Não consegui contabilizar as moedas desta run. Vou tentar de novo "
                                      "ao voltar ao cercado (detalhes em errors.log).")
            self.say("Erro ao fechar a run: moedas e Prestígio pendentes. Veja errors.log.", ttl=6.0)
            return None
        self.unsettled = None
        return summary

    def retry_settle(self) -> None:
        """Tenta de novo fechar a run que falhou antes; ao conseguir, grava o save."""
        if self.unsettled is None or self.save is None:
            return
        run, win, nodes = self.unsettled
        self.unsettled = None
        self.summary = self._settle(run, win, nodes)
        if self.unsettled is None and self.summary is not None:
            err = self.persist()
            self.say(f"Não consegui salvar: {err}" if err else "Run contabilizada.", "info" if not err else "error")

    # ------------------------------------------------------------ tempo
    def update(self, dt: float) -> None:
        eco = timing_mod.current().economy
        if self.shop:
            self.shop.update(dt)
        self.unlock_fx = update_fx(self.unlock_fx, dt)
        self.hud_flash = max(0.0, self.hud_flash - dt)
        if self.seal is not None:
            self.seal[1] += dt
            if self.seal[1] >= eco.seal_time:
                self.seal = None
        if self.summary is not None and self.mode == "resultado":
            self.summary.age += dt
        if self.toast:
            self.toast.ttl -= dt
            if self.toast.ttl <= 0:
                self.toast = None
        if self.col:
            self.col.update(dt)
        if self.mode == "cercado" and self.pen:
            self.pen.update(dt)
            self._drain_pen_sounds()
            self._pen_sync_clock += dt
            if self._pen_sync_clock >= 0.5:
                self._pen_sync_clock = 0.0
                self.sync_pen()
        if self.adopt:
            self.adopt.update(dt)
        if self.breed:
            self.breed.update(dt)
        if self.mode == "run" and self.rc:
            self.rc.update(dt)
            self._check_run_end()
