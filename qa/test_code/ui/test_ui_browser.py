"""UI — Tests de l'interface réelle (Streamlit dans Chrome, piloté par Playwright), captures d'écran réelles."""

import time

from conftest import (
    BY_ID,
    WELCOME,
    assistant_count,
    chip_labels,
    chip_locators,
    click,
    displayed_cards,
    last_assistant,
    send,
    shot,
    show_exchange,
    wait_idle,
)


def test_UI01_launch_and_welcome_screen(page, evidence):
    path = shot(page, "ui", "UI-01")
    title = page.title()
    welcome = page.locator(WELCOME).locator("h1").inner_text()
    meta = page.locator(".am-stats, .am-welcome-meta").first.inner_text()
    starters = page.locator('[class*="st-key-welcome_cards"] button').count()
    exc = page.locator('[data-testid="stException"]').count()
    evidence.update(title=title, welcome=welcome, meta=meta, starter_buttons=starters, exceptions=exc,
                    console_errors=page.console_errors, screenshot=path)
    assert "Findrive" in title
    assert welcome.startswith("Votre prochaine voiture")
    # innerText applique le text-transform CSS (majuscules sous Chrome/Linux) : comparaison sans casse
    assert "200 annonces" in " ".join(meta.lower().split()) and starters == 4 and exc == 0


def test_UI02_chat_input_and_user_message(page, evidence):
    box = page.get_by_test_id("stChatInputTextArea")
    visible, enabled = box.is_visible(), box.is_enabled()
    placeholder = box.get_attribute("placeholder")
    send(page, "Je cherche une voiture hybride")
    user_msgs = page.locator('[data-testid="stChatMessage"]').filter(has=page.locator('[data-testid="stChatMessageAvatarUser"]'))
    first_user = page.locator('[data-testid="stChatMessage"]').first.inner_text()
    show_exchange(page)
    path = shot(page, "ui", "UI-02")
    evidence.update(input_visible=visible, input_enabled=enabled, placeholder=placeholder,
                    user_bubble=first_user.strip()[:80], user_bubbles=user_msgs.count(),
                    input_cleared=box.input_value() == "", screenshot=path)
    assert visible and enabled and "voiture" in placeholder.lower()
    assert "Je cherche une voiture hybride" in first_user
    assert box.input_value() == ""


def test_UI03_assistant_message_and_cards(page, evidence):
    send(page, "Peugeot essence")
    reply = last_assistant(page)
    cards = displayed_cards(page)
    title = reply.locator(".am-a-title").inner_text()
    show_exchange(page)
    path = shot(page, "ui", "UI-03")
    card_shot = shot(page, "ui", "UI-03_card", reply.locator('[class*="st-key-card_"]').first)
    readable = all(c["name"] and "DT" in c["price_text"] and "km" in c["specs"] for c in cards)
    evidence.update(title=title, text=reply.locator(".am-a-text").inner_text(), cards=len(cards),
                    first_card=cards[0] if cards else None, readable=readable, screenshot=path,
                    screenshot_card=card_shot)
    assert title and cards and readable
    assert all(BY_ID[c["id"]]["marque"] == "Peugeot" and BY_ID[c["id"]]["carburant"] == "Essence" for c in cards)


def test_UI04_criteria_chips_display_and_removal(page, evidence):
    send(page, "Peugeot diesel à Tunis")
    before = chip_labels(page)
    show_exchange(page)
    path1 = shot(page, "ui", "UI-04_chips")
    chip = next(b for b in chip_locators(page) if "Tunis" in b.inner_text())
    click(page, chip)
    after = chip_labels(page)
    user_text = page.locator('[data-testid="stChatMessage"]').nth(assistant_count(page) - 2).inner_text()
    show_exchange(page)
    path2 = shot(page, "ui", "UI-04_after_removal")
    evidence.update(chips_before=before, chips_after=after, message_sent=user_text.strip()[:60],
                    screenshot=path1, screenshot_after=path2)
    assert sorted(before) == ["Diesel", "Peugeot", "Tunis"]
    assert sorted(after) == ["Diesel", "Peugeot"]
    assert "peu importe la ville" in user_text


def test_UI05_no_result_empty_state(page, evidence):
    send(page, "électrique à Gabès moins de 20000 DT")
    reply = last_assistant(page)
    empty = reply.locator(".am-empty")
    relax = reply.locator('[class*="st-key-relax_"] button')
    labels = [relax.nth(i).inner_text() for i in range(relax.count())]
    show_exchange(page)
    path = shot(page, "ui", "UI-05")
    evidence.update(empty_state=empty.count(), empty_text=empty.inner_text() if empty.count() else "",
                    suggestions=labels, screenshot=path)
    assert empty.count() == 1 and labels
    if labels:
        click(page, relax.first)
        assert displayed_cards(page), "une suggestion d'élargissement doit produire des résultats"


def test_UI06_loading_indicator(page, evidence):
    box = page.get_by_test_id("stChatInputTextArea")
    box.fill("voiture automatique à Sousse")
    box.press("Enter")
    seen, shot_path = False, None
    deadline = time.time() + 8
    while time.time() < deadline:
        if page.locator(".am-typing").count():
            seen = True
            text = page.locator(".am-typing").first.inner_text()
            shot_path = shot(page, "ui", "UI-06_loading")
            break
        time.sleep(0.03)
    wait_idle(page)
    gone = page.locator(".am-typing").count() == 0
    evidence.update(indicator_seen=seen, indicator_text=text if seen else None, gone_after=gone,
                    screenshot=shot_path)
    assert seen and gone


def test_UI07_pagination_show_more(page, evidence):
    send(page, "voiture à Tunis")
    first = len(displayed_cards(page))
    more = last_assistant(page).locator("button", has_text="de plus").first
    label = more.inner_text()
    more.click()
    time.sleep(0.4)
    wait_idle(page)
    second = len(displayed_cards(page))
    path = shot(page, "ui", "UI-07", last_assistant(page).locator("button", has_text="de plus").first)
    evidence.update(before=first, label=label, after=second, screenshot=path)
    assert first == 6 and second == 12 and "40 restantes" in label


def test_UI08_detail_sheet_open_close(page, evidence):
    send(page, "Toyota hybride")
    cards = displayed_cards(page)
    last_assistant(page).get_by_role("button", name="Voir les détails").first.click()
    time.sleep(0.4)
    wait_idle(page)
    detail = page.locator(".am-detail")
    name = detail.locator(".am-detail-name").inner_text() if detail.count() else ""
    ref = detail.inner_text() if detail.count() else ""
    show_exchange(page)
    path = shot(page, "ui", "UI-08_detail")
    n_open = assistant_count(page)
    page.get_by_role("button", name="Fermer la fiche").click()
    time.sleep(0.4)
    wait_idle(page)
    evidence.update(first_card=cards[0]["id"] if cards else None, detail_name=name,
                    reference_shown=bool(cards) and cards[0]["id"] in ref, messages_open=n_open,
                    messages_after_close=assistant_count(page), screenshot=path)
    assert cards and name == cards[0]["name"] and cards[0]["id"] in ref
    assert assistant_count(page) == n_open - 2


def test_UI09_new_conversation_reset(page, evidence):
    send(page, "diesel à Sfax")
    send(page, "moins de 50000 DT")
    n_before = assistant_count(page)
    # L'en-tête Streamlit (transparent) peut recouvrir la barre du haut selon la plateforme :
    # on déclenche l'événement click directement sur le bouton.
    page.locator('[class*="st-key-new_conv"] button').first.dispatch_event("click")
    time.sleep(0.5)
    wait_idle(page)
    path = shot(page, "ui", "UI-09")
    evidence.update(messages_before=n_before, messages_after=assistant_count(page),
                    welcome_back=page.locator(WELCOME).count(), screenshot=path)
    assert n_before == 4 and assistant_count(page) == 0 and page.locator(WELCOME).count() == 1
    send(page, "à Tunis")
    assert chip_labels(page) == ["Tunis"]


def test_UI10_multiple_searches_and_scroll(page, evidence):
    msgs = ["Je cherche une voiture diesel", "à Tunis seulement", "maximum 45000 DT", "plutôt à Sousse",
            "peu importe la ville", "Renault"]
    for m in msgs:
        send(page, m)
    time.sleep(1.0)
    last_user = page.locator('[data-testid="stChatMessage"]').nth(assistant_count(page) - 2)
    box = last_user.bounding_box()
    vh = page.viewport_size["height"]
    in_view = box is not None and box["y"] < vh and box["y"] + box["height"] > 0
    path = shot(page, "ui", "UI-10")
    evidence.update(messages=assistant_count(page), last_user_in_viewport=in_view,
                    last_user_y=box["y"] if box else None, chips=chip_labels(page),
                    exceptions=page.locator('[data-testid="stException"]').count(), screenshot=path)
    assert assistant_count(page) == 2 * len(msgs)
    assert in_view, "la conversation doit défiler vers le dernier échange"
    assert page.locator('[data-testid="stException"]').count() == 0
    assert page.get_by_test_id("stChatInputTextArea").is_enabled()


def test_UI11_responsive_mobile(browser, app_server, evidence):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                              has_touch=True, locale="fr-FR")
    pg = ctx.new_page()
    pg.goto(app_server)
    pg.wait_for_selector(WELCOME, timeout=60000)
    wait_idle(pg)
    p1 = shot(pg, "ui", "UI-11_mobile_welcome")
    send(pg, "diesel à Tunis")
    show_exchange(pg)
    p2 = shot(pg, "ui", "UI-11_mobile_results")
    overflow = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    card_box = pg.locator('[class*="st-key-card_"]').first.bounding_box()
    input_ok = pg.get_by_test_id("stChatInputTextArea").is_visible()
    evidence.update(horizontal_overflow_px=overflow, card_width=card_box["width"] if card_box else None,
                    input_visible=input_ok, screenshot=p1, screenshot_results=p2)
    ctx.close()
    assert overflow <= 1 and input_ok and card_box and card_box["width"] <= 390


def test_UI12_no_broken_images_or_errors(page, evidence):
    send(page, "SUV à Sfax")
    broken = page.evaluate("Array.from(document.images).filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)")
    svgs = page.locator('[class*="st-key-card_"] svg[role="img"]').count()
    cards = len(displayed_cards(page))
    exc = page.locator('[data-testid="stException"]').count()
    relevant = [e for e in page.console_errors if "favicon" not in e.lower()]
    evidence.update(broken_images=broken, card_illustrations=svgs, cards=cards, exceptions=exc,
                    console_errors=relevant)
    assert broken == [] and exc == 0 and svgs == cards > 0
    assert relevant == [], relevant
