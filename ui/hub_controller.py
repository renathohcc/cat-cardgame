"""Controlador do hub: menu inicial, colecao, run e resultado. Puro (sem pygame).

So chama a API publica do core (`new_game`, `read_save`, `write_save`) e delega a colecao ao
`CollectionController` e a run ao `RunController`. O save so e gravado entre runs: nada de
retomar run (fechar a janela no meio da run = run perdida, o save fica como estava).

Modos: "menu" | "colecao" | "run" | "adocao" | "resultado".
Elementos do menu: ("menu", "continue"|"new_game"|"quit") ("confirm_yes",) ("confirm_no",)
Resultado: ("result_back",)
"""
from __future__ import annotations

import os
from pathlib import Path
from random import Random

from core import (SaveData, create_adoption, has_pending_adoption, new_game, read_save,
                  write_save)
from core.types import IllegalAction
from core.types import Content
from ui import layout_hub as LH
from ui.adoption_controller import AdoptionController
from ui.collection_controller import CollectionController
from ui.controller import Toast
from ui.run_controller import RunController

DEFAULT_SAVE = Path(__file__).resolve().parent.parent / "saves" / "save.json"


class HubController:
    def __init__(self, content: Content, save_path: Path | str | None, seed: int, *,
                 ai_delay: float = 0.5) -> None:
        self.content = content
        self.save_path = Path(save_path) if save_path is not None else None   # None = so memoria
        self.seed = seed
        self.ai_delay = ai_delay
        self.mode = "menu"
        self.save: SaveData | None = None
        self.col: CollectionController | None = None
        self.rc: RunController | None = None
        self.adopt: AdoptionController | None = None
        self.load_error: str | None = None        # texto do erro quando o save esta corrompido
        self.has_file = False
        self.confirm_new = False
        self.wants_quit = False
        self.toast: Toast | None = None
        self.result_text = ""
        self.result_win = False
        self.result_detail: list[str] = []
        self.runs_started = 0
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
            self.load_error = str(e) or type(e).__name__

    def persist(self) -> str | None:
        """Grava o save; devolve texto de erro (ou None). Sem caminho = nao grava."""
        if self.save is None or self.save_path is None:
            return None
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            write_save(self.save, self.save_path)
        except Exception as e:  # noqa: BLE001 - qualquer falha vira aviso, nunca derruba o jogo
            return str(e) or type(e).__name__
        self.has_file = True
        return None

    def adopt_save(self, save: SaveData) -> None:
        self.save = save
        self.load_error = None
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

    # ------------------------------------------------------------ entrada
    def hit(self, pos: tuple[int, int]) -> tuple | None:
        m = self.mode
        if m == "run":
            return self.rc.hit(pos) if self.rc else None
        if m == "menu":
            return LH.hit_test(pos, m, confirm=self.confirm_new)
        if m == "colecao":
            return self.col.hit(pos)
        if m == "adocao":
            return self.adopt.hit(pos)
        return LH.hit_test(pos, m)

    def click(self, elem: tuple | None) -> None:
        m = self.mode
        if m == "run" and self.rc:
            self.rc.click(elem)
            self._check_run_end()
        elif m == "menu":
            self._click_menu(elem)
        elif m == "colecao":
            act = self.col.click(elem)
            if act == "back":
                self.mode = "menu"
            elif act == "start":
                self.start_run()
        elif m == "adocao":
            if self.adopt.click(elem) == "done":
                self._finish_adoption()
        elif m == "resultado" and elem == ("result_back",):
            self.mode = "colecao"

    def _click_menu(self, elem: tuple | None) -> None:
        if self.confirm_new:
            if elem == ("confirm_yes",):
                self.confirm_new = False
                self.start_new_game()
            elif elem == ("confirm_no",):
                self.confirm_new = False
            return
        if not elem or elem[0] != "menu":
            return
        item = elem[1]
        if item == "continue" and self.can_continue:
            self.col = CollectionController(self.content, self.save, self.persist)
            self.mode = "colecao"
            self.open_pending_adoption()
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
        self.mode = "adocao"
        return True

    def _finish_adoption(self) -> None:
        toast = self.adopt.toast if self.adopt else None
        self.adopt = None
        self.mode = "colecao"
        if self.col is None:
            self.col = CollectionController(self.content, self.save, self.persist)
        self.col.toast = toast
        rows = self.col.rows()
        if self.col.selected_cat() is None and rows:
            self.col.selected = rows[0].cat.id

    def start_new_game(self) -> None:
        bak_err = self.backup_save()
        self.adopt_save(new_game(self.content, Random(self.seed)))
        err = self.persist()
        self.mode = "colecao"
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
        m = self.mode
        if m == "menu":
            self.confirm_new = False
        elif m == "colecao":
            if self.col.editing:
                self.col.cancel_rename()
            elif self.col.confirm_donate:
                self.col.confirm_donate = False
            else:
                self.mode = "menu"
        elif m == "run" and self.rc:
            self.rc.cancel()
            self._check_run_end()
        elif m == "adocao":
            self.adopt = None            # a oferta fica no save; "Continuar" reabre
            self.mode = "menu"
        elif m == "resultado":
            self.mode = "colecao"

    def key_enter(self) -> None:
        m = self.mode
        if m == "colecao":
            if self.col.editing:
                self.col.confirm_rename()
        elif m == "run" and self.rc:
            self.rc.confirm_key()
            self._check_run_end()
        elif m == "resultado":
            self.mode = "colecao"

    def text_input(self, text: str) -> None:
        if self.mode == "colecao":
            self.col.type_text(text)

    def backspace(self) -> None:
        if self.mode == "colecao":
            self.col.backspace()

    def scroll(self, n: int) -> None:
        if self.mode == "adocao":
            self.adopt.scroll_by(n)
        if self.mode == "colecao" and not self.col.editing:
            self.col.scroll_by(n)

    @property
    def editing_text(self) -> bool:
        return self.mode == "colecao" and self.col is not None and self.col.editing

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
        if rc.abandoned:
            self.result_detail.append("Você abandonou a run (conta como derrota).")
        elif rc.end_line:
            self.result_detail.append(f"{rc.end_line[0]}: \"{rc.end_line[1]}\"")
        result = "abandono" if rc.abandoned else rc.run.result
        self.rc = None
        try:
            create_adoption(self.content, self.save, Random(self.seed * 7919 + self.runs_started),
                            result, n)
        except IllegalAction as e:      # ja havia oferta pendente: mantem a antiga
            self.say(str(e))
        err = self.persist()            # UM unico write_save
        if err:
            self.say(f"Não consegui salvar: {err}")
        if self.open_pending_adoption():
            return
        self.result_detail.append("Nenhum gato para adotar desta vez")
        self.mode = "resultado"

    # ------------------------------------------------------------ tempo
    def update(self, dt: float) -> None:
        if self.toast:
            self.toast.ttl -= dt
            if self.toast.ttl <= 0:
                self.toast = None
        if self.col:
            self.col.update(dt)
        if self.adopt:
            self.adopt.update(dt)
        if self.mode == "run" and self.rc:
            self.rc.update(dt)
            self._check_run_end()
