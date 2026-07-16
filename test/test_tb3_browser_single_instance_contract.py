from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_canonical_launcher_enforces_one_browser_page():
    script = (REPO_ROOT / "scripts" / "start_touch_gui_host.sh").read_text()

    assert "--new-window" not in script
    assert "--application-mode" not in script
    assert "run_epiphany_guarded.sh" in script
    assert "--property=Restart=no" in script
    assert '--property="BindsTo=$OPENBOX_UNIT"' in script
    assert "session_state.xml" in script
    assert "pkill -x epiphany" in script
    assert '[[ "$(browser_process_count)" -eq 1 ]]' in script
    assert '[[ "$(webkit_page_count)" -eq 1 ]]' in script


def test_desktop_launcher_delegates_to_canonical_launcher():
    launcher = (REPO_ROOT / "deploy" / "tb3" / "start_tb3_web_ui.sh").read_text()
    installer = (REPO_ROOT / "deploy" / "tb3" / "install.sh").read_text()

    assert "scripts/start_touch_gui_host.sh" in launcher
    assert 'exec bash "$START_SCRIPT" "$URL"' in launcher
    assert 'install -m 0755 "$SCRIPT_DIR/start_tb3_web_ui.sh"' in installer


def test_browser_guard_tracks_xorg_and_openbox_lifecycle():
    guard = (REPO_ROOT / "scripts" / "run_epiphany_guarded.sh").read_text()

    assert 'DISPLAY="$DISPLAY_VALUE" xset q' in guard
    assert 'systemctl --user is-active --quiet "$OPENBOX_UNIT"' in guard
    assert 'epiphany-browser --profile="$PROFILE_DIR" "$URL"' in guard
    assert "stopping Epiphany" in guard
