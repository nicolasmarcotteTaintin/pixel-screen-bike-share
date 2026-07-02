from pixel_transit.lcd.menu import (
    MODE_KEYS,
    ROTATE_OPTIONS,
    SCREEN_SIZE,
    BrightnessScreen,
    info_screen,
    language_menu,
    main_menu,
    minutes_to_hhmm,
    mode_menu,
    rotate_menu,
    sleep_screen,
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


def test_main_menu_options():
    keys = [key for key, _, _ in main_menu("fr").options]
    assert keys == ["mode", "rotate", "brightness", "lcd_brightness",
                    "sleep", "language", "info", "exit"]
    labels = {key: label for key, label, _ in main_menu("fr").options}
    assert labels["brightness"] == "Luminosité écran"
    assert labels["lcd_brightness"] == "Luminosité Pi"


def test_alternance_disabled_unless_alternating_mode():
    assert main_menu("fr").is_disabled("rotate")
    assert main_menu("fr", mode="velo").is_disabled("rotate")
    assert not main_menu("fr", mode="velo_communauto").is_disabled("rotate")


def test_rotate_menu_keys_and_active():
    menu = rotate_menu("fr", active_seconds=20)
    assert [int(key) for key, _, _ in menu.options] == list(ROTATE_OPTIONS)
    assert menu.current_key == "20"


def test_info_screen_renders():
    screen = info_screen("fr", {"host": "pi", "ip": "10.0.0.2"})
    assert screen.render().size == (SCREEN_SIZE, SCREEN_SIZE)


def test_sleep_screen_toggle_and_time_steps():
    screen = sleep_screen("fr", enabled=True, off_start="21:00", off_end="08:00")
    assert screen.enabled is True
    screen.adjust(1)              # field 0 = state -> toggles off
    assert screen.enabled is False
    screen.move(1)               # field 1 = off time
    screen.adjust(1)             # +30 min
    assert minutes_to_hhmm(screen.off_minutes) == "21:30"
    screen.move(1)               # field 2 = on time
    screen.adjust(-1)            # -30 min, wraps within day
    assert minutes_to_hhmm(screen.on_minutes) == "07:30"


def test_minutes_hhmm_roundtrip():
    assert minutes_to_hhmm(21 * 60) == "21:00"
    assert minutes_to_hhmm(0) == "00:00"
    assert minutes_to_hhmm(24 * 60) == "00:00"


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
