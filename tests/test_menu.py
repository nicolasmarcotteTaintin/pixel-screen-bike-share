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
    rotate_screen,
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


def test_move_clamps_no_wrap():
    menu = mode_menu("fr")
    menu.move(-1)                       # already at the top -> stays
    assert menu.selected == 0
    for _ in range(len(MODE_KEYS) + 2):
        menu.move(1)                    # past the end -> clamps at the last item
    assert menu.selected == len(MODE_KEYS) - 1


def test_active_key_sets_initial_selection():
    assert mode_menu("fr", active_key="communauto").current_key == "communauto"
    assert language_menu(active_key="en").current_key == "en"


def test_main_menu_options():
    keys = [key for key, _, _ in main_menu("fr").options]
    assert keys == ["mode", "rotate", "brightness", "lcd_brightness",
                    "sleep", "language", "info", "exit"]
    # French and English must expose the exact same options (same keys, same order).
    assert [k for k, _, _ in main_menu("en").options] == keys
    labels = {key: label for key, label, _ in main_menu("fr").options}
    assert labels["brightness"] == "Luminosité écran"
    assert labels["lcd_brightness"] == "Luminosité Pi"


def test_menu_edge_scrolling():
    m = main_menu("fr")               # 8 options, window of 5
    assert m._window() == (0, 5)
    for _ in range(4):
        m.move(1)                     # down to index 4 = last visible row
    assert m.selected == 4 and m._window()[0] == 0   # window hasn't moved yet
    m.move(1)                         # index 5 -> scroll down by one
    assert m.selected == 5 and m._window()[0] == 1
    m.move(1)
    m.move(1)                         # index 7 (last) -> window at bottom
    assert m.selected == 7 and m._window()[0] == 3
    m.move(1)                         # already at the last item -> stays, no wrap
    assert m.selected == 7 and m._window()[0] == 3


def test_alternance_disabled_unless_alternating_mode():
    assert main_menu("fr").is_disabled("rotate")
    assert main_menu("fr", mode="velo").is_disabled("rotate")
    assert not main_menu("fr", mode="velo_communauto").is_disabled("rotate")


def test_rotate_screen_steps_and_clamps():
    screen = rotate_screen("fr", 10)
    assert screen.value == 10
    screen.adjust(1)
    assert screen.value == 15
    for _ in range(10):
        screen.adjust(-1)
    assert screen.value == ROTATE_OPTIONS[0]   # clamped low
    for _ in range(20):
        screen.adjust(1)
    assert screen.value == ROTATE_OPTIONS[-1]  # clamped high
    assert rotate_screen("fr", 12).value in (10, 15)  # snaps to nearest option


def test_info_screen_renders():
    screen = info_screen("fr", {"host": "pi", "ip": "10.0.0.2"})
    assert screen.render().size == (SCREEN_SIZE, SCREEN_SIZE)


def test_sleep_screen_fields_and_sunset():
    s = sleep_screen("fr", enabled=True, off_start="21:00", off_end="08:00")
    assert s.enabled is True and s.sunset is False
    s.adjust(1)                       # field 0 = state -> off
    assert s.enabled is False
    s.field = 1; s.adjust(1)          # field 1 = trigger -> sunset
    assert s.sunset is True
    s.field = 2; before = s.off_minutes; s.adjust(1)   # off time ignored while sunset
    assert s.off_minutes == before
    s.field = 1; s.adjust(1)          # trigger -> fixed again
    assert s.sunset is False
    s.field = 2; s.adjust(1)          # off time +30
    assert minutes_to_hhmm(s.off_minutes) == "21:30"
    s.field = 3; s.adjust(-1)         # on time -30
    assert minutes_to_hhmm(s.on_minutes) == "07:30"


def test_sleep_screen_from_sunset_config():
    s = sleep_screen("fr", enabled=True, off_start="sunset", off_end="08:00")
    assert s.sunset is True


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
