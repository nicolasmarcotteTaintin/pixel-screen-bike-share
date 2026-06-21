from pixel_transit.lcd.menu import (
    MODE_KEYS,
    SCREEN_SIZE,
    language_menu,
    mode_menu,
)


def test_mode_keys_order():
    menu = mode_menu("fr")
    assert [key for key, _, _ in menu.options] == list(MODE_KEYS)


def test_language_menu_options():
    menu = language_menu()
    assert [key for key, _, _ in menu.options] == ["fr", "en"]


def test_mode_menu_is_localized():
    assert mode_menu("fr").options[0][1] == "Vélo"
    assert mode_menu("en").options[0][1] == "Bike"
    # Unknown language falls back to French.
    assert mode_menu("xx").title == mode_menu("fr").title


def test_move_wraps():
    menu = mode_menu("fr")
    menu.move(-1)
    assert menu.selected == len(MODE_KEYS) - 1
    menu.move(1)
    assert menu.selected == 0


def test_active_key_sets_initial_selection():
    assert mode_menu("fr", active_key="communauto").current_key == "communauto"
    assert language_menu(active_key="en").current_key == "en"


def test_render_sizes():
    assert mode_menu("en", active_key="velo").render().size == (SCREEN_SIZE, SCREEN_SIZE)
    assert language_menu(active_key="fr").render(confirmed=True).size == (SCREEN_SIZE, SCREEN_SIZE)
