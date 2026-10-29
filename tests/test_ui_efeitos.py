"""Testes da UI nova da T3.4: efeitos com alvo, Espiritos, buffs, inimigo-pessoa, textos,
layout e fluxos por cliques aleatorios. Sem janela (SDL dummy), pelos pontos de entrada
`Controller.click` e `settle()`.

Escritos a partir de reports/T3.4-ui-efeitos.md, do GDD e dos contratos; o estado final e
sempre conferido na API publica do core (`view`, `legal_actions`, `sides`).
"""
from __future__ import annotations

import os
from random import Random

import pytest

from core import roll_cat
from core.duel import (
    attack_targets, card_from_effect, card_from_special, legal_actions, view,
)
from core.types import (
    AtkBuffExpired, AtkBuffed, Attack, DeckSpec, Drew, EffectPlayed, EnergyChanged, Healed,
    LeaderHealed, PlayCat, PlayEffect,
)
from duel_helpers import duel, fc, load, mk
from ui import layout as L
from ui import text as T
from ui.controller import Controller

PLAYER, ENEMY = "player", "enemy"
ENEMY_IDS = ["tonho-sem-sorte", "irmaos-pimenta", "berenice-da-matilha", "madame-fifi-pelucia"]


@pytest.fixture(scope="module")
def content():
    return load()


def eff(content, eid):
    return card_from_effect(content, eid)


def spi(content, sid):
    return card_from_special(content, sid)


def ctrl_with(content, seed: int = 1, enemy_id: str | None = None, **kw) -> Controller:
    """Controlador sobre um duelo montado (turno do jogador, parado, pronto para agir)."""
    c = Controller(content, seed, ai_delay=0.0, enemy_id=enemy_id)
    kw.setdefault("player_deck", [mk(1, 1), mk(1, 1)])      # evita Impasse por mesa vazia
    kw.setdefault("enemy_deck", [mk(1, 1), mk(1, 1)])
    c.duel = duel(content, **kw)
    c.phase = "play"
    c.beats.clear()
    c.cur = None
    c.fx = []
    c.toast = None
    c.banner = None
    c.refresh()
    return c


def snap(c: Controller):
    d = c.duel
    return (view(d, PLAYER), view(d, ENEMY), len(d.log), d.turn_side, d.winner)


def run_until(c: Controller, pred, steps: int = 4000, dt: float = 0.1) -> bool:
    for _ in range(steps):
        if pred(c):
            return True
        c.update(dt)
    return pred(c)


def me(c: Controller):
    return c.duel.sides[PLAYER]


def foe(c: Controller):
    return c.duel.sides[ENEMY]


# ================================================================= 1. efeitos com alvo
def test_dano_em_gato_inimigo_clicando_na_carta_e_no_alvo(content):
    c = ctrl_with(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=3,
                  enemy_field={2: fc(1, 5)})
    c.click(("hand", 0))
    assert c.sel == ("hand", 0)
    assert c.sel_targets == [("slot", 2)]
    assert c.targeting() and c.slot_target(ENEMY, 2) == "ALVO"
    c.click(("slot", ENEMY, 2))
    assert foe(c).field[2].hp == 2                       # 3 de dano
    assert me(c).energy == 1 and me(c).hand == []
    assert c.sel is None


def test_cura_em_gato_aliado_clicando_na_carta_e_no_alvo(content):
    c = ctrl_with(content, player_hand=[eff(content, "lambida-curativa")], player_energy=3,
                  player_field={1: fc(2, 2, hp_max=6)})
    c.click(("hand", 0))
    assert ("slot", 1) in c.sel_targets
    assert c.slot_target(PLAYER, 1) == "ALVO"
    c.click(("slot", PLAYER, 1))
    assert me(c).field[1].hp == 5                        # +3
    assert me(c).energy == 2


def test_buff_de_atk_em_gato_aliado(content):
    c = ctrl_with(content, player_hand=[eff(content, "rugido-de-guerra")], player_energy=3,
                  player_field={0: fc(2, 3)})
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 0))
    assert me(c).field[0].atk == 4
    assert me(c).energy == 2 and me(c).hand == []


def test_dano_em_lider_inimigo_clicando_no_lider(content):
    c = ctrl_with(content, player_hand=[eff(content, "bote-no-lider")], player_energy=3,
                  enemy_leader_hp=10, enemy_field={0: fc(1, 5, kw=("provocar",))})
    c.click(("hand", 0))
    assert c.leader_target(ENEMY) == "effect" and c.leader_target(PLAYER) is None
    c.click(("leader", ENEMY))
    assert foe(c).leader_hp == 6                         # ignora Provocar
    assert me(c).energy == 0


def test_cura_no_proprio_lider(content):
    c = ctrl_with(content, player_hand=[eff(content, "soneca-no-sol")], player_energy=3,
                  player_leader_hp=10)
    c.click(("hand", 0))
    assert c.leader_target(PLAYER) == "effect" and c.leader_target(ENEMY) is None
    c.click(("leader", PLAYER))
    assert me(c).leader_hp == 14
    assert me(c).energy == 1


@pytest.mark.parametrize("clique", [("slot", PLAYER, 0), ("slot", ENEMY, 4), ("leader", ENEMY),
                                    ("leader", PLAYER), ("slot", PLAYER, 3)])
def test_alvo_invalido_nao_joga_o_efeito(content, clique):
    c = ctrl_with(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=3,
                  player_field={0: fc(2, 2)}, enemy_field={1: fc(1, 5)})
    antes = snap(c)
    c.click(("hand", 0))
    c.click(clique)
    assert snap(c) == antes
    assert len(me(c).hand) == 1
    assert c.toast is not None


def test_cura_em_alvo_inimigo_nao_joga(content):
    c = ctrl_with(content, player_hand=[eff(content, "lambida-curativa")], player_energy=3,
                  player_field={0: fc(2, 2, hp_max=6)}, enemy_field={0: fc(1, 1, hp_max=5)})
    antes = snap(c)
    c.click(("hand", 0))
    c.click(("slot", ENEMY, 0))
    assert snap(c) == antes


@pytest.mark.parametrize("como", ["cancel", "click_none", "click_vazio", "mesma_carta"])
def test_esc_botao_direito_e_clique_no_vazio_cancelam_o_efeito(content, como):
    c = ctrl_with(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=3,
                  enemy_field={0: fc(1, 5)})
    antes = snap(c)
    c.click(("hand", 0))
    assert c.sel is not None
    {"cancel": c.cancel,                                  # ESC e botao direito chamam cancel()
     "click_none": lambda: c.click(None),
     "click_vazio": lambda: c.click(("none",)),
     "mesma_carta": lambda: c.click(("hand", 0))}[como]()
    assert c.sel is None and c.sel_targets == []
    assert snap(c) == antes


@pytest.mark.parametrize("eid,ganho", [("petisco-surpresa", None), ("cochilo-revigorante", 2)])
def test_efeito_sem_alvo_usa_o_segundo_clique_na_carta(content, eid, ganho):
    deck = [mk(1, 1), mk(2, 2)]
    c = ctrl_with(content, player_hand=[eff(content, eid)], player_deck=deck, player_energy=3)
    c.click(("hand", 0))
    assert c.sel == ("hand", 0) and c.needs_confirm()
    assert me(c).hand and len(me(c).hand) == 1            # ainda nao usou
    c.click(("hand", 0))
    assert c.sel is None
    if ganho is None:                                     # comprar 1: sai o efeito, entra um gato
        assert len(me(c).hand) == 1 and me(c).hand[0].kind == "cat"
        assert me(c).energy == 2
    else:                                                 # energia: -1 de custo, +2
        assert me(c).hand == [] and me(c).energy == 3 - 1 + ganho


def test_efeito_sem_alvo_nao_gasta_no_clique_em_outro_lugar(content):
    c = ctrl_with(content, player_hand=[eff(content, "cochilo-revigorante")], player_energy=3,
                  enemy_field={0: fc(1, 1)})
    antes = snap(c)
    c.click(("hand", 0))
    c.click(("slot", ENEMY, 0))                           # nao e o segundo clique na carta
    c.click(("leader", ENEMY))
    assert snap(c) == antes


@pytest.mark.parametrize("eid", ["arranhao-certeiro", "petisco-surpresa", "bote-no-lider",
                                 "soneca-no-sol"])
def test_efeito_sem_energia_suficiente_nao_joga(content, eid):
    c = ctrl_with(content, player_hand=[eff(content, eid)], player_energy=0,
                  player_leader_hp=10, player_field={0: fc(2, 2, hp_max=5)},
                  enemy_field={0: fc(1, 5)}, player_deck=[mk(1, 1)])
    antes = snap(c)
    c.click(("hand", 0))
    assert c.sel is None
    assert c.toast is not None and "energia" in c.toast.text.lower()
    ok, motivo = c.hand_state(0)
    assert ok is False and motivo[0] == "FALTAM"
    c.click(("slot", ENEMY, 0))
    c.click(("hand", 0))
    assert snap(c) == antes


def test_efeito_com_alvo_sem_alvo_valido_mostra_sem_alvo_valido(content):
    c = ctrl_with(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=3)
    ok, motivo = c.hand_state(0)
    assert ok is False and motivo == ["SEM ALVO", "VÁLIDO"]
    antes = snap(c)
    c.click(("hand", 0))
    assert c.sel is None and c.toast is not None
    assert snap(c) == antes


def test_efeito_jogado_aparece_no_log_e_a_carta_sai_da_mao_mostrada(content):
    c = ctrl_with(content, player_hand=[eff(content, "arranhao-certeiro"), mk(1, 1)],
                  player_energy=3, enemy_field={0: fc(1, 5)})
    c.click(("hand", 0))
    c.click(("slot", ENEMY, 0))
    c.settle()
    assert any("Arranhão Certeiro" in t for t, _ in c.log)
    assert [h.kind for h in c.shown.me.hand] == ["cat"]
    assert c.shown == view(c.duel, PLAYER)


# ================================================================= 2. Espiritos
def espirito_trovao(content, **kw):
    kw.setdefault("player_energy", 3)
    kw.setdefault("enemy_field", {2: fc(1, 5)})
    return ctrl_with(content, player_hand=[spi(content, "trovao-amarelo")], **kw)


def test_espirito_com_alvo_clica_carta_slot_e_depois_o_alvo(content):
    c = espirito_trovao(content)
    c.click(("hand", 0))
    assert c.sel == ("hand", 0)
    assert c.playable[0] == {0, 1, 2, 3, 4}
    c.click(("slot", PLAYER, 1))
    assert c.sel == ("enter", 0, 1)
    assert c.targeting()
    assert me(c).field[1] is None and len(me(c).hand) == 1      # ainda nao jogou
    assert c.spirit_ghost() is not None and c.spirit_ghost()[0] == 1
    assert c.spirit_ghost()[1].ref == "trovao-amarelo"
    assert c.sel_targets == [("slot", 2)] and c.slot_target(ENEMY, 2) == "ALVO"
    c.click(("slot", ENEMY, 2))
    assert me(c).field[1].card.ref == "trovao-amarelo"
    assert foe(c).field[2].hp == 3                              # 2 de dano ao entrar
    assert me(c).energy == 0 and me(c).hand == []
    assert c.sel is None and c.spirit_ghost() is None


def test_espirito_sem_alvo_valido_entra_direto_com_aviso(content):
    c = espirito_trovao(content, enemy_field={})
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 3))
    assert c.sel is None
    assert me(c).field[3] is not None and me(c).field[3].card.ref == "trovao-amarelo"
    assert c.toast is not None and c.toast.kind == "warn"
    assert "Sem alvo válido" in c.toast.text


def test_espirito_sem_escolha_de_alvo_entra_direto_sem_aviso(content):
    c = ctrl_with(content, player_hand=[spi(content, "guardiao-bigodudo")], player_energy=3,
                  player_leader_hp=10, enemy_field={0: fc(1, 5)})
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 0))
    assert me(c).field[0].card.ref == "guardiao-bigodudo"
    assert me(c).leader_hp == 13                                # cura 3 no Lider ao entrar
    assert c.toast is None


def test_espirito_que_compra_e_que_da_energia_entram_direto(content):
    c = ctrl_with(content, player_hand=[spi(content, "velha-dos-novelos"),
                                        spi(content, "soneca-ancestral")],
                  player_deck=[mk(1, 1)], player_energy=5)
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 0))
    assert me(c).field[0].card.ref == "velha-dos-novelos"
    assert any(h.kind == "cat" for h in me(c).hand)             # comprou 1
    i = next(k for k, h in enumerate(me(c).hand) if h.ref == "soneca-ancestral")
    c.settle()
    energia = me(c).energy
    c.click(("hand", i))
    c.click(("slot", PLAYER, 1))
    assert me(c).energy == energia - 2 + 1


def test_espirito_dano_no_lider_inimigo_ao_entrar(content):
    c = ctrl_with(content, player_hand=[spi(content, "gata-das-brasas")], player_energy=7,
                  enemy_leader_hp=10)
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 2))
    assert me(c).field[2].card.ref == "gata-das-brasas"
    assert foe(c).leader_hp == 7


def test_espirito_sem_efeito_ao_entrar_entra_direto(content):
    c = ctrl_with(content, player_hand=[spi(content, "sombra-miuda")], player_energy=3,
                  enemy_field={0: fc(1, 1)})
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 0))
    assert me(c).field[0].card.ref == "sombra-miuda" and c.toast is None


def test_cancelar_o_espirito_depois_de_clicar_a_carta(content):
    c = espirito_trovao(content)
    antes = snap(c)
    c.click(("hand", 0))
    c.cancel()
    assert c.sel is None and snap(c) == antes


@pytest.mark.parametrize("como", ["cancel", "click_none", "click_vazio", "mesma_carta"])
def test_cancelar_o_espirito_na_etapa_do_alvo_nao_gasta_nada(content, como):
    c = espirito_trovao(content)
    antes = snap(c)
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 1))
    assert c.sel == ("enter", 0, 1)
    {"cancel": c.cancel, "click_none": lambda: c.click(None),
     "click_vazio": lambda: c.click(("none",)),
     "mesma_carta": lambda: c.click(("hand", 0))}[como]()
    assert c.sel is None and c.sel_targets == [] and c.spirit_ghost() is None
    assert snap(c) == antes
    assert me(c).field[1] is None and me(c).energy == 3


@pytest.mark.parametrize("clique", [("leader", ENEMY), ("leader", PLAYER), ("slot", PLAYER, 3),
                                    ("slot", ENEMY, 0), ("slot", PLAYER, 1)])
def test_clique_fora_dos_alvos_na_etapa_do_alvo_mantem_o_pedido(content, clique):
    c = espirito_trovao(content)
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 1))
    antes = snap(c)
    c.click(clique)
    assert snap(c) == antes
    assert c.sel == ("enter", 0, 1)


def test_arrastar_espirito_para_o_slot_pede_o_alvo(content):
    c = espirito_trovao(content)
    assert c.draggable(("hand", 0))
    assert c.drag_start(("hand", 0))
    c.drop(("slot", PLAYER, 4))
    assert c.sel == ("enter", 0, 4)
    c.click(("slot", ENEMY, 2))
    assert me(c).field[4].card.ref == "trovao-amarelo"
    assert foe(c).field[2].hp == 3


def test_arrastar_espirito_para_destino_invalido_cancela(content):
    c = espirito_trovao(content)
    antes = snap(c)
    assert c.drag_start(("hand", 0))
    c.drop(("slot", ENEMY, 2))
    assert c.sel is None and snap(c) == antes


def test_arrastar_efeito_sem_alvo_e_efeito_com_alvo_nao_quebra(content):
    c = ctrl_with(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=3,
                  enemy_field={0: fc(1, 5)})
    assert c.drag_start(("hand", 0))
    c.drop(("slot", ENEMY, 0))                                  # soltar no alvo joga
    assert foe(c).field[0].hp == 2


def test_espirito_sem_energia_nao_seleciona(content):
    c = espirito_trovao(content, player_energy=2)
    antes = snap(c)
    c.click(("hand", 0))
    assert c.sel is None and c.toast is not None
    assert snap(c) == antes


def test_espirito_com_campo_cheio_avisa_sem_slot(content):
    campo = {n: fc(1, 1, ready=False) for n in range(5)}
    c = espirito_trovao(content, player_field=campo)
    ok, motivo = c.hand_state(0)
    assert not ok and motivo == ["SEM SLOT", "VAZIO"]


# ================================================================= 3. buffs, cura, eventos
def test_buff_temporario_fica_destacado_e_some_na_expiracao(content):
    c = ctrl_with(content, player_hand=[eff(content, "rugido-de-guerra")], player_energy=3,
                  player_field={0: fc(2, 3)}, enemy_field={0: fc(1, 9)})
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 0))
    textos: list[str] = []
    mid: list[int] = []
    for _ in range(600):                                        # anima o buff passo a passo
        c.update(0.05)
        textos += [f.text for f in c.fx]
        if c.shown.me.field[0] and c.shown.me.field[0].atk_bonus_turn:
            mid.append(c.shown.me.field[0].atk_bonus_turn)
        if c.can_act():
            break
    assert "+2 ATK" in textos
    assert set(mid) == {2}
    sh = c.shown.me.field[0]
    assert sh.atk == 4 and sh.atk_bonus_turn == 2 == me(c).field[0].atk_bonus_turn
    c.end_turn()                                                # expira no fim do turno do dono
    seen: list[str] = []
    while not (c.can_act() or c.over):
        c.update(0.05)
        seen += [f.text for f in c.fx]
    assert "-2 ATK" in seen
    assert any("bônus" in t for t, _ in c.log)
    fcg = me(c).field[0]
    if fcg is not None:                                         # sobreviveu ao turno inimigo
        assert fcg.atk == 2 and fcg.atk_bonus_turn == 0
        assert c.shown.me.field[0].atk_bonus_turn == 0
        assert c.shown.me.field[0].atk == 2
    assert any(isinstance(e, AtkBuffExpired) for e in c.duel.log)


def test_cura_de_lider_atualiza_a_tela_e_o_log(content):
    c = ctrl_with(content, player_hand=[eff(content, "soneca-no-sol")], player_energy=3,
                  player_leader_hp=10)
    c.click(("hand", 0))
    c.click(("leader", PLAYER))
    textos = []
    while not c.can_act():
        c.update(0.05)
        textos += [f.text for f in c.fx]
    assert "+4" in textos
    assert c.shown.me.leader_hp == 14 == me(c).leader_hp
    assert any("Seu Líder recupera 4" in t for t, _ in c.log)


def test_eventos_novos_sao_tratados_sem_excecao_e_atualizam_a_tela(content):
    c = ctrl_with(content, player_hand=[mk(1, 1)], player_deck=[mk(1, 1)],
                  player_field={0: fc(2, 3)}, enemy_field={0: fc(1, 5, hp_max=8)},
                  player_leader_hp=10)
    rug, bote = eff(content, "rugido-de-guerra"), eff(content, "bote-no-lider")
    evs = [EffectPlayed(PLAYER, rug, ("slot", 0)), AtkBuffed(PLAYER, 0, 2, 4, True),
           AtkBuffExpired(PLAYER, 0, 2, 2), LeaderHealed(PLAYER, 3, 13),
           EffectPlayed(ENEMY, bote, ("leader",)), AtkBuffed(ENEMY, 0, 1, 2, False),
           Healed(ENEMY, 0, 2, 7), EnergyChanged(PLAYER, 5), Drew(PLAYER, mk(1, 1)),
           EffectPlayed(ENEMY, spi(content, "trovao-amarelo"), ("slot", 0))]
    for ev in evs:
        T.describe(ev, c.shown)                                # nao levanta
    c._enqueue(evs)
    assert run_until(c, lambda x: not x.beats and x.cur is None, dt=0.2)
    assert c.shown.me.leader_hp == 13
    assert c.shown.me.field[0].atk_bonus_turn == 0 and c.shown.me.field[0].atk == 2
    assert c.shown.opponent.field[0].atk == 2 and c.shown.opponent.field[0].hp == 7


def test_evento_de_buff_em_slot_vazio_nao_levanta(content):
    c = ctrl_with(content)
    c._enqueue([AtkBuffed(PLAYER, 3, 1, 3, True), AtkBuffExpired(ENEMY, 2, 1, 1),
                Healed(PLAYER, 1, 1, 1)])
    assert run_until(c, lambda x: not x.beats and x.cur is None, dt=0.2)


# ================================================================= 4. inimigo-pessoa
@pytest.mark.parametrize("eid", ENEMY_IDS)
def test_inimigo_pessoa_tem_nome_e_tipo_vindos_do_data(content, eid):
    c = Controller(content, 3, enemy_id=eid)
    data = content.enemies[eid]
    assert c.enemy is data
    assert c.enemy_name() == data["nome"]
    assert c.enemy["tipo"] in ("batalha", "elite", "chefe")


def test_sem_inimigo_o_nome_e_generico_e_nao_ha_fala(content):
    c = Controller(content, 3)
    assert c.enemy is None and c.enemy_name() == "Inimigo" and c.final_line is None


def test_etiquetas_elite_e_chefe_so_para_esses_tipos():
    from ui.render import _TIPO_TAG
    assert _TIPO_TAG == {"elite": "ELITE", "chefe": "CHEFE"}


def test_tipos_dos_inimigos_reais(content):
    tipos = {e: content.enemies[e]["tipo"] for e in ENEMY_IDS}
    assert tipos["berenice-da-matilha"] == "elite"
    assert tipos["madame-fifi-pelucia"] == "chefe"
    assert tipos["tonho-sem-sorte"] == "batalha"


def test_regra_do_chefe_banho_de_espuma_tem_texto_e_so_no_chefe(content):
    c = Controller(content, 3, enemy_id="madame-fifi-pelucia")
    rule = c.shown.opponent.rule
    assert rule is not None and rule["id"] == "banho-de-espuma"
    assert T.rule_name(rule).lower() == "banho de espuma"
    texto = T.rule_text(rule)
    assert texto and "1" in texto and "Líder" in texto
    assert c.shown.me.rule is None
    for eid in ("tonho-sem-sorte", "irmaos-pimenta", "berenice-da-matilha"):
        assert Controller(content, 3, enemy_id=eid).shown.opponent.rule is None


def test_rule_name_deriva_do_id_quando_nao_ha_nome():
    assert T.rule_name({"id": "banho-de-espuma"}) == "Banho de Espuma"


def test_rule_name_usa_o_nome_do_data_sem_alterar(content):
    rule = Controller(content, 3, enemy_id="madame-fifi-pelucia").shown.opponent.rule
    assert T.rule_name(rule) == "Banho de Espuma" == rule["nome"]
    assert T.rule_name({"id": "x", "nome": "Outro Nome"}) == "Outro Nome"


def test_rule_text_usa_o_texto_do_data_quando_existe():
    rule = {"id": "x", "texto": "Texto escrito no data.",
            "gatilho": "inicio_turno_proprio",
            "acao": {"tipo": "cura", "alvo": "lider_proprio", "valor": 1}}
    assert T.rule_text(rule) == "Texto escrito no data."


def test_rule_text_gera_a_frase_da_acao_quando_nao_ha_texto():
    rule = {"id": "banho-de-espuma", "gatilho": "inicio_turno_proprio",
            "acao": {"tipo": "cura", "alvo": "lider_proprio", "valor": 1}}
    texto = T.rule_text(rule)
    assert texto and "1" in texto and "Líder" in texto


def test_regra_do_chefe_cura_o_lider_dele_no_turno_dele_e_o_log_mostra(content):
    c = Controller(content, 5, enemy_id="madame-fifi-pelucia", ai_delay=0.0)
    c.settle()
    foe(c).leader_hp = 10
    c.refresh()
    c.end_turn()
    c.settle()
    assert foe(c).leader_hp > 10
    assert c.shown.opponent.leader_hp == foe(c).leader_hp
    assert any("Líder inimigo recupera" in t for t, _ in c.log)


def _ctrl_enemy(content, eid, seed, **kw):
    return ctrl_with(content, seed=seed, enemy_id=eid, **kw)


@pytest.mark.parametrize("eid", ENEMY_IDS)
def test_fala_final_de_derrota_do_inimigo_quando_o_jogador_vence(content, eid):
    c = _ctrl_enemy(content, eid, 4, player_field={0: fc(5, 5)}, enemy_leader_hp=3)
    c.click(("slot", PLAYER, 0))
    c.click(("leader", ENEMY))
    assert run_until(c, lambda x: x.final_visible)
    assert c.duel.winner == PLAYER
    falas = content.enemies[eid]["falas"]
    assert c.final_line in falas["derrota"]
    assert c.final_line == Random(4 + 2).choice(falas["derrota"])


@pytest.mark.parametrize("eid", ENEMY_IDS)
def test_fala_final_de_vitoria_do_inimigo_quando_o_jogador_perde(content, eid):
    c = _ctrl_enemy(content, eid, 6, player_leader_hp=1,
                    enemy_field={0: fc(5, 5)}, player_field={})
    c.end_turn()
    assert run_until(c, lambda x: x.final_visible)
    assert c.duel.winner == ENEMY
    falas = content.enemies[eid]["falas"]
    assert c.final_line in falas["vitoria"]
    assert c.final_line == Random(6 + 2).choice(falas["vitoria"])


def test_fala_final_e_deterministica_por_seed_e_varia_entre_seeds(content):
    def fala(seed):
        c = _ctrl_enemy(content, "tonho-sem-sorte", seed, player_field={0: fc(5, 5)},
                        enemy_leader_hp=3)
        c.click(("slot", PLAYER, 0))
        c.click(("leader", ENEMY))
        run_until(c, lambda x: x.final_visible)
        return c.final_line
    assert fala(11) == fala(11)
    todas = {fala(s) for s in range(1, 25)}
    assert todas == set(content.enemies["tonho-sem-sorte"]["falas"]["derrota"])


def test_sem_inimigo_pessoa_nao_ha_fala_no_fim(content):
    c = ctrl_with(content, player_field={0: fc(5, 5)}, enemy_leader_hp=3)
    c.click(("slot", PLAYER, 0))
    c.click(("leader", ENEMY))
    assert run_until(c, lambda x: x.final_visible)
    assert c.final_line is None


def test_repetir_zera_a_fala_e_sorteia_de_novo_pela_mesma_seed(content):
    c = _ctrl_enemy(content, "tonho-sem-sorte", 4, player_field={0: fc(5, 5)}, enemy_leader_hp=3)
    c.click(("slot", PLAYER, 0))
    c.click(("leader", ENEMY))
    run_until(c, lambda x: x.final_visible)
    assert c.final_line
    c.repeat()
    assert c.final_line is None and c.enemy_id == "tonho-sem-sorte"
    assert c.line_rng.random() == Random(6).random()


# ================================================================= 5. ui/text.py
def _todos_efeitos(content):
    return [card_from_effect(content, e) for e in sorted(content.effects)]


def _todos_espiritos(content):
    return [card_from_special(content, s) for s in sorted(content.specials)]


def test_ha_8_efeitos_e_8_espiritos_reais(content):
    assert len(content.effects) == 8 and len(content.specials) == 8


def test_textos_de_todas_as_acoes_dos_efeitos_e_espiritos_reais(content):
    total = 0
    for card in _todos_efeitos(content) + _todos_espiritos(content):
        for act in card.actions:
            head, tgt = T.action_short(act)
            assert isinstance(head, str) and head.strip(), (card.ref, act)
            assert isinstance(tgt, str)
            assert T.action_sentence(act).strip(), (card.ref, act)
            total += 1
    assert total >= 8 + 5


def test_card_summary_nunca_vazio_para_efeitos_e_espiritos_com_acao(content):
    for card in _todos_efeitos(content):
        assert card.actions and T.card_summary(card), card.ref
        assert T.card_sentences(card), card.ref
        assert all(isinstance(s, str) and s for s in T.card_summary(card))
    for card in _todos_espiritos(content):
        if card.actions:
            assert T.card_summary(card) and T.card_sentences(card), card.ref
        else:                                                   # sem "ao entrar": nao levanta
            assert T.card_summary(card) == [] and T.card_sentences(card) == []


def test_resumo_traz_o_valor_e_o_alvo_certos():
    assert T.action_short({"tipo": "dano", "alvo": "inimigo_escolhido", "valor": 3}) == \
        ("3 DANO", "gato inimigo")
    assert T.action_short({"tipo": "cura", "alvo": "lider_proprio", "valor": 4})[0] == "CURA 4"
    assert T.action_short({"tipo": "comprar", "alvo": "nenhum", "valor": 2})[0] == "COMPRA 2"
    assert "2" in T.action_short({"tipo": "energia", "alvo": "nenhum", "valor": 2})[0]
    assert "+2 ATK" == T.action_short({"tipo": "buff_atk", "alvo": "aliado_escolhido",
                                       "valor": 2, "duracao": "turno"})[0]


def test_acao_de_regra_dos_inimigos_reais_tem_texto(content):
    for e in content.enemies.values():
        if e.get("regra_propria"):
            assert T.rule_name(e["regra_propria"]) and T.rule_text(e["regra_propria"])


def test_frases_de_efeito_mencionam_o_valor(content):
    for card in _todos_efeitos(content):
        for act in card.actions:
            assert str(act["valor"]) in T.action_sentence(act), (card.ref, act)


# ================================================================= 6. layout
def test_final_panel_novo_cabe_em_960x540_e_tem_o_tamanho_esperado():
    p = L.final_panel()
    assert (p.x, p.y, p.w, p.h) == (180, 60, 600, 420)
    assert pygame_rect(0, 0, 960, 540).contains(p)


def pygame_rect(*a):
    import pygame
    return pygame.Rect(*a)


def test_botoes_do_painel_final_continuam_dentro_do_painel_maior():
    p, b = L.final_panel(), L.final_buttons()
    for r in b.values():
        assert p.contains(r) and pygame_rect(0, 0, 960, 540).contains(r)
    assert not b["again"].colliderect(b["repeat"])
    for name, r in b.items():
        assert L.hit_test(r.center, 3, final=True) == (name,)


def _cena(cena, enemy, tmp_path, monkeypatch, seed=1):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from ui.__main__ import main
    out = tmp_path / f"{cena}-{enemy}.png"
    args = ["--seed", str(seed), "--screenshot", str(out), "--cena", cena]
    if enemy:
        args += ["--inimigo", enemy]
    assert main(args) == 0
    data = out.read_bytes()
    assert len(data) > 1000 and data[:8] == b"\x89PNG\r\n\x1a\n"
    import pygame
    img = pygame.image.load(str(out))
    assert img.get_size() == (960, 540)
    cores = {tuple(img.get_at((x, y)))[:3] for x in range(0, img.get_width(), 19)
             for y in range(0, img.get_height(), 19)}
    assert len(cores) > 3


@pytest.mark.parametrize("cena", ["efeito", "espirito", "chefe"])
def test_cenas_novas_geram_png(cena, tmp_path, monkeypatch):
    _cena(cena, None, tmp_path, monkeypatch)


@pytest.mark.parametrize("eid", ENEMY_IDS)
def test_cena_final_com_cada_inimigo_gera_png(eid, tmp_path, monkeypatch):
    _cena("final", eid, tmp_path, monkeypatch)


@pytest.mark.parametrize("eid", ENEMY_IDS)
def test_cena_inicio_e_chefe_com_cada_inimigo_geram_png(eid, tmp_path, monkeypatch):
    _cena("inicio", eid, tmp_path, monkeypatch, seed=2)
    _cena("chefe", eid, tmp_path, monkeypatch, seed=2)


@pytest.mark.parametrize("cena", ["efeito", "espirito"])
@pytest.mark.parametrize("eid", ENEMY_IDS)
def test_cenas_efeito_e_espirito_com_cada_inimigo_geram_png(cena, eid, tmp_path, monkeypatch):
    _cena(cena, eid, tmp_path, monkeypatch, seed=3)


def test_desenho_com_hover_em_tudo_nas_cenas_novas_nao_levanta(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame
    pygame.init()
    from ui import scenes_novas
    from ui.render import UIState, draw_frame
    canvas = pygame.Surface((960, 540))
    for cena in scenes_novas.NEW_SCENES:
        ctrl = scenes_novas.make(1, cena)
        assert ctrl is not None
        n = len(ctrl.shown.me.hand)
        pontos = [L.hand_rect(i, n).center for i in range(n)]
        pontos += [L.leader_rect(s).center for s in (PLAYER, ENEMY)]
        pontos += [L.slot_rect(s, k).center for s in (PLAYER, ENEMY) for k in range(5)]
        for pos in pontos:
            draw_frame(canvas, ctrl, UIState(t=0.3, mouse=pos))


# ================================================================= 7. propriedade
def player_spec(content, seed: int) -> DeckSpec:
    rng = Random(seed)
    cards = [eff(content, e) for e in ("arranhao-certeiro", "rugido-de-guerra",
                                       "lambida-curativa", "soneca-no-sol", "petisco-surpresa",
                                       "bote-no-lider")]
    cards += [spi(content, s) for s in ("trovao-amarelo", "guardiao-bigodudo",
                                        "velha-dos-novelos", "gata-das-brasas")]
    cats = []
    for i in range(12 - len(cards)):
        cat = roll_cat(content, rng)
        cat.id = f"p{i + 1}"
        cats.append(cat)
    return DeckSpec(cats=cats, cards=cards)


def random_click(c: Controller, rng: Random) -> tuple | None:
    if c.targeting() and c.sel_targets and rng.random() < 0.5:
        t = rng.choice(c.sel_targets)
        if t[0] == "leader":
            return ("leader", rng.choice([PLAYER, ENEMY]))
        return ("slot", rng.choice([PLAYER, ENEMY]), t[1])
    n_hand = len(c.shown.me.hand)
    r = rng.random()
    if r < 0.08:
        return ("pass",)
    if r < 0.40 and n_hand:
        return ("hand", rng.randrange(n_hand))
    if r < 0.46:
        return ("hand", rng.randrange(0, 12))
    if r < 0.64:
        return ("slot", PLAYER, rng.randrange(5))
    if r < 0.82:
        return ("slot", ENEMY, rng.randrange(5))
    if r < 0.90:
        return ("leader", rng.choice([PLAYER, ENEMY]))
    if r < 0.94:
        return rng.choice([None, ("none",)])
    return ("pass_no",)


def check_consistent(c: Controller) -> None:
    d = c.duel
    rules = c.content.rules["duel"]
    for side in (PLAYER, ENEMY):
        st = d.sides[side]
        assert len(st.field) == rules["slots"]
        assert len(st.hand) <= rules["hand_max"]
        assert 0 <= st.energy <= rules["energy_cap"]
        assert 0 <= st.leader_hp <= st.leader_hp_max or d.winner is not None
    if not c.can_act():
        return
    assert c.shown == view(d, PLAYER)
    jogaveis = {a.hand_index for a in legal_actions(d) if isinstance(a, (PlayCat, PlayEffect))}
    assert set(c.playable) == jogaveis
    assert c.attackers == {a.attacker_slot for a in legal_actions(d) if isinstance(a, Attack)}
    if c.sel and c.sel[0] == "slot":
        assert set(c.sel_targets) == set(attack_targets(d, c.sel[1]))
    if c.sel and c.sel[0] in ("hand", "enter"):
        assert c.sel[1] < len(d.sides[PLAYER].hand)
        alvos = {a.target for a in legal_actions(d)
                 if isinstance(a, (PlayCat, PlayEffect)) and a.hand_index == c.sel[1]
                 and a.target is not None}
        assert set(c.sel_targets) <= alvos
    if c.sel and c.sel[0] == "enter":
        assert d.sides[PLAYER].field[c.sel[2]] is None
        assert c.spirit_ghost() is not None
    else:
        assert c.spirit_ghost() is None


@pytest.mark.parametrize("eid", ENEMY_IDS)
@pytest.mark.parametrize("seed", range(1, 51))
def test_duelo_so_por_cliques_aleatorios_contra_inimigo_real_termina_consistente(
        content, eid, seed):
    c = Controller(content, seed, ai_delay=0.0, enemy_id=eid,
                   player_spec=player_spec(content, seed))
    rng = Random(seed * 7919 + 13)
    guard = 0
    while not c.over and guard < 4000:
        guard += 1
        c.settle()
        if c.over:
            break
        c.click(random_click(c, rng))
        check_consistent(c)
        if guard % 20 == 0 and c.can_act():
            c.end_turn()
    c.settle()
    assert c.over, f"duelo {eid}/{seed} nao terminou"
    assert c.duel.winner in (PLAYER, ENEMY)
    assert c.summary()
    assert c.shown.winner == c.duel.winner
    falas = content.enemies[eid]["falas"]
    chave = "vitoria" if c.duel.winner == ENEMY else "derrota"
    assert c.final_line in falas[chave]
