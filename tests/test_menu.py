from pixel_transit.lcd.menu import MENU_OPTIONS, SCREEN_SIZE, Menu


def test_options_match_modes():
    assert [key for key, _, _ in MENU_OPTIONS] == ["velo", "velo_communauto", "communauto"]


def test_move_wraps():
    menu = Menu()
    assert menu.selected == 0
    menu.move(-1)
    assert menu.selected == len(MENU_OPTIONS) - 1
    menu.move(1)
    assert menu.selected == 0


def test_active_key_sets_initial_selection():
    menu = Menu(active_key="communauto")
    assert menu.current_key == "communauto"


def test_select_index_and_current_key():
    menu = Menu()
    menu.select_index(1)
    assert menu.current_key == "velo_communauto"
    menu.select_index(99)  # out of range -> ignored
    assert menu.current_key == "velo_communauto"


def test_render_size():
    image = Menu(active_key="velo").render()
    assert image.size == (SCREEN_SIZE, SCREEN_SIZE)
