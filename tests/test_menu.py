from pixel_transit.lcd.menu import (
    MODE_KEYS,
    SCREEN_SIZE,
    BrightnessScreen,
    language_menu,
    main_menu,
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


def test_main_menu_has_brightness():
    keys = [key for key, _, _ in main_menu("fr").options]
    assert keys == ["mode", "brightness", "language"]
    assert main_menu("en").options[1][1] == "Brightness"


def test_brightness_adjust_and_clamp():
    screen = BrightnessScreen(80)
    screen.adjust(1)
    assert screen.value == 85
    for _ in range(10):
        screen.adjust(1)
    assert screen.value == 100  # clamped high
    for _ in range(30):
        screen.adjust(-1)
    assert screen.value == 0    # clamped low


def test_render_sizes():
    assert mode_menu("en", active_key="velo").render().size == (SCREEN_SIZE, SCREEN_SIZE)
    assert language_menu(active_key="fr").render(confirmed=True).size == (SCREEN_SIZE, SCREEN_SIZE)
    assert main_menu("fr").render().size == (SCREEN_SIZE, SCREEN_SIZE)
    assert BrightnessScreen(40, lang="en").render(confirmed=True).size == (SCREEN_SIZE, SCREEN_SIZE)
