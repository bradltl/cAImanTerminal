use crate::terminal_backend::TerminalSurface;
use crate::{
    context::{bounded, CommandRecord, Session},
    shell::{self, EventReader},
    worker::{self, Event, Request},
};
use gtk::{gdk, gio, glib, prelude::*};
use std::{
    cell::{Cell, RefCell},
    fs,
    path::PathBuf,
    rc::Rc,
    sync::{
        atomic::{AtomicU64, Ordering},
        mpsc::SyncSender,
        Arc,
    },
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};
use vte::prelude::*;

// A read-only text buffer shares the terminal's typography and colors. Model
// output is plain text, never terminal escape sequences or executable input.
struct AssistantPane {
    view: gtk::TextView,
    conversation: RefCell<Vec<String>>,
    current: RefCell<String>,
}
impl AssistantPane {
    fn set_text(&self, text: &str) {
        let redacted = crate::context::redact(text);
        let text = redacted.as_str();
        if *self.current.borrow() == text {
            return;
        }
        *self.current.borrow_mut() = text.to_string();
        self.render(false);
    }
    fn user_message(&self, text: &str) {
        let text = crate::context::redact(text);
        self.conversation
            .borrow_mut()
            .push(format!("@ {}", text.trim_start()));
        self.current.borrow_mut().clear();
        if self.conversation.borrow().len() > 100 {
            self.conversation.borrow_mut().remove(0);
        }
        self.render(true);
    }
    fn response(&self, text: &str, passive: bool) {
        if passive {
            self.set_text(text);
        } else {
            self.conversation
                .borrow_mut()
                .push(crate::context::redact(text));
            if self.conversation.borrow().len() > 100 {
                self.conversation.borrow_mut().remove(0);
            }
            self.current.borrow_mut().clear();
            self.render(false);
        }
    }
    fn current_text(&self) -> String {
        self.current.borrow().clone()
    }
    fn render(&self, force_scroll: bool) {
        let follow = force_scroll
            || self
                .view
                .vadjustment()
                .is_none_or(|a| a.value() + a.page_size() >= a.upper() - 24.0);
        let mut text = self.conversation.borrow().join("\n\n");
        let current = self.current.borrow();
        if !current.is_empty() {
            if !text.is_empty() {
                text.push_str("\n\n");
            }
            text.push_str(&current);
        }
        self.view.buffer().set_text(&text);
        if follow {
            let mut end = self.view.buffer().end_iter();
            self.view.scroll_to_iter(&mut end, 0.0, false, 0.0, 1.0);
        }
    }
    #[cfg(test)]
    fn text(&self) -> String {
        let buffer = self.view.buffer();
        buffer
            .text(&buffer.start_iter(), &buffer.end_iter(), false)
            .to_string()
    }
}

struct Suggestion {
    command: String,
    input: String,
    ticket: u64,
    binding: crate::context::ContextBinding,
}
struct Tab {
    session: Session,
    terminal: vte::Terminal,
    assistant: AssistantPane,
    ghost: gtk::Label,
    status: gtk::Label,
    activity: gtk::Label,
    pane: gtk::Revealer,
    dir: tempfile::TempDir,
    reader: EventReader,
    cancellation: Arc<AtomicU64>,
    pending: Option<Suggestion>,
    running: Option<(String, String, i64, bool)>,
    staged: Option<String>,
    suggested: Option<String>,
    start_row: i64,
    edited: Instant,
    passive_ticket: Option<u64>,
    snapshot_pending: bool,
    snapshot_waiting: bool,
    followup: Option<String>,
    enabled: bool,
    idle_delay: Duration,
    shell: &'static dyn crate::adapters::ShellIntegration,
    child: Option<glib::Pid>,
    alive: bool,
    closed: bool,
}
impl Tab {
    fn invalidate(&mut self) {
        self.cancellation.fetch_add(1, Ordering::Relaxed);
        self.pending = None;
        self.ghost.set_text("");
        self.activity.set_text("ai");
        if self.enabled
            && self.assistant.current_text() != "Loading.."
            && self.assistant.current_text() != "Ready.."
        {
            self.assistant.set_text("Ready..");
        }
        self.edited = Instant::now();
        self.snapshot_pending = true;
    }
    fn accept(&mut self) -> bool {
        let Some(s) = self.pending.take() else {
            return false;
        };
        self.ghost.set_text("");
        if !self.session.at_prompt
            || !self.alive
            || self.closed
            || self.session.remote
            || s.ticket != self.cancellation.load(Ordering::Relaxed)
            || !s.binding.matches(&self.session)
        {
            return false;
        }
        match shell::write_stage_bound(
            self.dir.path(),
            &s.command,
            &s.input,
            &self.session.cwd,
            self.session.prompt_generation,
        ) {
            Ok(()) => {
                // Fixed widget key sequence only. Never feed model text or Enter.
                self.terminal.send_integration_key(self.shell.stage_key());
                self.terminal.grab_focus();
                true
            }
            Err(e) => {
                self.assistant.set_text(&format!("Could not stage: {e}"));
                false
            }
        }
    }
    fn request(&mut self, text: String, passive: bool, requests: &SyncSender<Request>) {
        if !self.session.at_prompt || self.session.remote {
            return;
        }
        if !passive {
            self.assistant.user_message(&text);
        }
        if !self.enabled {
            self.assistant.response("Off.", passive);
            return;
        }
        let ticket = self.cancellation.fetch_add(1, Ordering::Relaxed) + 1;
        self.session.request_id = ticket;
        self.pending = None;
        self.ghost.set_text("");
        let remember_intent = !passive || !self.session.input.is_empty();
        let memory = format!("User: {text}");
        let mut session = self.session.clone();
        // Read VTE directly at the request boundary. Shell journal entries alone
        // miss text from interactive programs and output since the last prompt.
        let screen = self.terminal.context_text();
        session.capture_terminal(
            &screen,
            self.running
                .as_ref()
                .map(|(command, _, _, _)| command.as_str()),
        );
        if remember_intent {
            session.remember(memory.clone());
        }
        let req = Request {
            session,
            text,
            ticket,
            cancellation: self.cancellation.clone(),
            passive,
        };
        match requests.try_send(req) {
            Ok(()) => {
                if remember_intent {
                    self.session.remember(memory);
                }
                self.passive_ticket = Some(ticket);
                self.activity.set_text("ai · thinking");
                self.followup = None;
                if !passive {
                    self.assistant.set_text("Thinking..");
                }
            }
            Err(std::sync::mpsc::TrySendError::Full(_)) => {
                if !passive {
                    self.assistant.response("Busy. Try again shortly.", false);
                }
            }
            Err(std::sync::mpsc::TrySendError::Disconnected(_)) => {
                self.passive_ticket = Some(ticket);
                self.assistant
                    .response("AI unavailable. Restart to reload the model.", passive);
            }
        }
    }
    fn poll(&mut self, requests: &SyncSender<Request>) {
        let events = match self.reader.poll(&self.dir.path().join("events")) {
            Ok(events) => events,
            Err(e) => {
                self.invalidate();
                self.enabled = false;
                self.status
                    .set_text(&format!("Shell integration unavailable: {e}"));
                self.session.at_prompt = false;
                return;
            }
        };
        for event in events {
            if self.session.prompt_generation != event.prompt_generation {
                self.invalidate();
                self.session.revision += 1;
                self.session.prompt_generation = event.prompt_generation;
            }
            if self.session.cwd != event.cwd
                || event.kind == "request"
                || (event.kind == "prompt" && (!self.session.at_prompt || self.session.remote))
            {
                self.invalidate();
                self.session.revision += 1;
            }
            self.session.cwd = event.cwd.clone();
            match event.kind.as_str() {
                "prompt" => {
                    if let Some((command, cwd, start_row, ai_origin)) = self.running.take() {
                        let (_, row) = self.terminal.cursor_position();
                        let (text, _) = self.terminal.text_range_format(
                            vte::Format::Text,
                            (start_row + 1).max(row - 150).min(row),
                            0,
                            row,
                            -1,
                        );
                        self.followup = crate::host::followup_request(
                            &command,
                            event.status,
                            ai_origin,
                            false, // The original local Bash prompt has now returned.
                        );
                        self.edited = Instant::now();
                        self.session.record(CommandRecord {
                            command,
                            cwd,
                            exit_code: event.status,
                            output: bounded(text.as_deref().unwrap_or(""), 2500),
                            timestamp: SystemTime::now()
                                .duration_since(UNIX_EPOCH)
                                .unwrap_or_default()
                                .as_secs(),
                            ai_origin,
                        });
                    }
                    self.session.remote = false;
                    self.session.at_prompt = true;
                    self.session.edit(String::new());
                    self.status
                        .set_text(&format!("{}  |  exit {}", self.session.cwd, event.status));
                }
                "start" => {
                    self.invalidate();
                    self.followup = None;
                    self.snapshot_pending = false;
                    self.snapshot_waiting = false;
                    self.session.at_prompt = false;
                    self.session.edit(String::new());
                    // All running programs, wrappers and nested shells are unknown.
                    // Only our original local Readline prompt resumes assistance.
                    let remote = true;
                    self.session.remote = remote;
                    let ai_origin = self.staged.take().is_some_and(|s| s == event.text)
                        || self.suggested.as_deref() == Some(event.text.trim());
                    self.running = Some((event.text, event.cwd, self.start_row, ai_origin));
                    self.status.set_text(if remote {
                        "running / host unknown | assistance paused"
                    } else {
                        "running"
                    });
                }
                "request" => {
                    self.snapshot_pending = false;
                    self.snapshot_waiting = false;
                    self.followup = None;
                    // @ is intercepted by Readline, so Bash is still at its prompt.
                    self.session.at_prompt = true;
                    self.session.edit(String::new());
                    self.request(event.text, false, requests);
                }
                "input" | "staged" => {
                    if event.kind == "staged" {
                        self.staged = Some(event.text.clone());
                    }
                    self.snapshot_waiting = false;
                    if self.session.input != event.text {
                        self.cancellation.fetch_add(1, Ordering::Relaxed);
                        self.pending = None;
                        self.ghost.set_text("");
                        self.session.edit(event.text);
                    }
                    if event.kind == "staged" {
                        self.passive_ticket = Some(self.cancellation.load(Ordering::Relaxed));
                    }
                }
                _ => {}
            }
        }
        // Readline's bind-x redraws the line. Read once after an idle interval,
        // never on every key release; do not infer against an unread edit.
        if self.enabled
            && self.snapshot_pending
            && !self.snapshot_waiting
            && self.session.at_prompt
            && self.alive
            && self.edited.elapsed() >= Duration::from_millis(150)
        {
            self.snapshot_pending = false;
            self.snapshot_waiting = true;
            self.terminal
                .send_integration_key(self.shell.snapshot_key());
        }
        let ticket = self.cancellation.load(Ordering::Relaxed);
        if self.enabled
            && self.session.at_prompt
            && !self.session.remote
            && !self.snapshot_pending
            && !self.snapshot_waiting
            && self.edited.elapsed() >= self.idle_delay
            && self.passive_ticket != Some(ticket)
        {
            if self.session.input.is_empty() {
                if let Some(text) = self.followup.clone() {
                    self.request(text, true, requests);
                }
            } else if crate::host::passive_eligible(&self.session.input, true, false) {
                self.request(self.session.input.clone(), true, requests);
            }
        }
    }
}
impl Drop for Tab {
    fn drop(&mut self) {
        self.cancellation.fetch_add(1, Ordering::Relaxed);
        if let Some(pid) = self.child {
            unsafe {
                libc::kill(pid.0, libc::SIGHUP);
            }
        }
    }
}
fn label(text: &str) -> gtk::Label {
    let label = gtk::Label::new(Some(text));
    label.set_wrap(true);
    label.set_xalign(0.0);
    label.set_selectable(true);
    label
}
fn new_tab(
    notebook: &gtk::Notebook,
    id: u64,
    requests: SyncSender<Request>,
    enabled: bool,
    options: &crate::settings::Settings,
) -> anyhow::Result<Rc<RefCell<Tab>>> {
    let dir = tempfile::Builder::new()
        .prefix("cayman-session-")
        .tempdir()?;
    let reader = EventReader::create(dir.path())?;
    let shell_adapter = crate::adapters::shell(&options.shell)?;
    fs::write(dir.path().join("bashrc"), shell_adapter.bootstrap())?;
    let terminal = vte::Terminal::new();
    terminal.set_hexpand(true);
    terminal.set_vexpand(true);
    terminal.set_scrollback_lines(options.scrollback as i64);
    terminal.set_font(Some(&gtk::pango::FontDescription::from_string(&format!(
        "Monospace {}",
        options.font_size
    ))));
    apply_terminal_theme(&terminal, crate::theme::default_theme());
    terminal.set_margin_start(6);
    terminal.set_margin_end(6);
    terminal.set_margin_top(6);
    let scroll = gtk::ScrolledWindow::builder()
        .child(&terminal)
        .hexpand(true)
        .vexpand(true)
        .build();
    let ghost = label("");
    ghost.add_css_class("ghost");
    // Reserve one line so suggestions cannot resize the PTY or reflow output.
    ghost.set_single_line_mode(true);
    ghost.set_ellipsize(gtk::pango::EllipsizeMode::End);
    ghost.set_height_request(22);
    let status = label("bash");
    status.add_css_class("status");
    let left = gtk::Box::new(gtk::Orientation::Vertical, 0);
    left.append(&scroll);
    left.append(&ghost);
    left.append(&status);
    let side = gtk::Box::new(gtk::Orientation::Vertical, 0);
    side.set_size_request(260, -1);
    let view = gtk::TextView::builder()
        .editable(false)
        .cursor_visible(false)
        .monospace(true)
        .wrap_mode(gtk::WrapMode::WordChar)
        .left_margin(8)
        .right_margin(8)
        .top_margin(6)
        .bottom_margin(6)
        .build();
    view.add_css_class("assistant-terminal");
    let assistant = AssistantPane {
        view: view.clone(),
        conversation: RefCell::new(Vec::new()),
        current: RefCell::new(String::new()),
    };
    assistant.set_text(if enabled { "Loading.." } else { "Off." });
    let side_scroll = gtk::ScrolledWindow::builder()
        .child(&view)
        .vexpand(true)
        .hexpand(true)
        .hscrollbar_policy(gtk::PolicyType::Never)
        .build();
    side.append(&side_scroll);
    let pane_label = label("ai");
    pane_label.add_css_class("status");
    side.append(&pane_label);
    let pane = gtk::Revealer::builder()
        .child(&side)
        .reveal_child(enabled && options.show_ai)
        .visible(enabled && options.show_ai)
        .transition_type(gtk::RevealerTransitionType::None)
        .build();
    let split = gtk::Paned::new(gtk::Orientation::Horizontal);
    split.set_start_child(Some(&left));
    split.set_end_child(Some(&pane));
    split.set_position(900);
    split.set_resize_end_child(false);
    split.set_shrink_start_child(false);
    let title_box = gtk::Box::new(gtk::Orientation::Horizontal, 8);
    title_box.append(&gtk::Label::new(Some(&format!("{id}: bash"))));
    let close = gtk::Button::from_icon_name("window-close-symbolic");
    close.add_css_class("flat");
    close.set_tooltip_text(Some("Close tab (Ctrl+Shift+W)"));
    title_box.append(&close);
    let index = notebook.append_page(&split, Some(&title_box));
    notebook.set_tab_reorderable(&split, true);
    notebook.set_current_page(Some(index));
    let cwd = std::env::current_dir()?.display().to_string();
    let tab = Rc::new(RefCell::new(Tab {
        session: Session::new(id, cwd.clone()),
        terminal: terminal.clone(),
        assistant,
        ghost,
        status,
        activity: pane_label,
        pane,
        dir,
        reader,
        cancellation: Arc::new(AtomicU64::new(0)),
        pending: None,
        running: None,
        staged: None,
        suggested: None,
        start_row: 0,
        edited: Instant::now(),
        passive_ticket: None,
        snapshot_pending: false,
        snapshot_waiting: false,
        followup: None,
        enabled,
        idle_delay: Duration::from_millis(options.idle_ms),
        shell: shell_adapter,
        child: None,
        alive: true,
        closed: false,
    }));
    let weak = Rc::downgrade(&tab);
    let book = notebook.clone();
    let page = split.clone();
    close.connect_clicked(move |_| {
        if let Some(tab) = weak.upgrade() {
            let mut tab = tab.borrow_mut();
            if !tab.session.at_prompt && tab.alive {
                tab.assistant.set_text(
                    "A command is running. Stop it or exit the shell before closing this tab.",
                );
                return;
            }
            tab.alive = false;
            tab.closed = true;
            tab.invalidate();
            if let Some(pid) = tab.child.take() {
                unsafe {
                    libc::kill(pid.0, libc::SIGHUP);
                }
            }
            if let Some(index) = book.page_num(&page) {
                book.remove_page(Some(index));
            }
        }
    });
    let keys = gtk::EventControllerKey::new();
    keys.set_propagation_phase(gtk::PropagationPhase::Capture);
    let weak = Rc::downgrade(&tab);
    keys.connect_key_pressed(move |_, key, _, modifiers| {
        let Some(tab) = weak.upgrade() else {
            return glib::Propagation::Proceed;
        };
        let mut tab = tab.borrow_mut();
        if modifiers.contains(gdk::ModifierType::CONTROL_MASK | gdk::ModifierType::SHIFT_MASK) {
            if key == gdk::Key::C || key == gdk::Key::c {
                tab.terminal.copy_clipboard_format(vte::Format::Text);
                return glib::Propagation::Stop;
            }
            if key == gdk::Key::V || key == gdk::Key::v {
                tab.invalidate();
                tab.terminal.paste_clipboard();
                return glib::Propagation::Stop;
            }
        }
        if key == gdk::Key::Tab
            && !modifiers.intersects(
                gdk::ModifierType::CONTROL_MASK
                    | gdk::ModifierType::ALT_MASK
                    | gdk::ModifierType::SHIFT_MASK,
            )
            && tab.accept()
        {
            return glib::Propagation::Stop;
        }
        if tab.session.at_prompt
            && ![
                gdk::Key::Shift_L,
                gdk::Key::Shift_R,
                gdk::Key::Control_L,
                gdk::Key::Control_R,
                gdk::Key::Alt_L,
                gdk::Key::Alt_R,
            ]
            .contains(&key)
        {
            tab.invalidate();
            if key == gdk::Key::Return
                || key == gdk::Key::KP_Enter
                || (modifiers.contains(gdk::ModifierType::CONTROL_MASK)
                    && [gdk::Key::j, gdk::Key::m, gdk::Key::o].contains(&key))
            {
                tab.start_row = tab.terminal.cursor_position().1;
                tab.session.at_prompt = false;
            }
        }
        glib::Propagation::Proceed
    });
    terminal.add_controller(keys);
    let weak = Rc::downgrade(&tab);
    terminal.connect_child_exited(move |_, status| {
        if let Some(tab) = weak.upgrade() {
            let mut tab = tab.borrow_mut();
            tab.invalidate();
            tab.child = None;
            tab.alive = false;
            tab.session.at_prompt = false;
            tab.status.set_text(&format!(
                "Shell exited ({status}) · close this tab or open another"
            ));
        }
    });
    let rcfile = tab.borrow().dir.path().join("bashrc");
    let session_env = format!("CAYMAN_SESSION_DIR={}", tab.borrow().dir.path().display());
    let weak = Rc::downgrade(&tab);
    let argv = shell_adapter.argv(&rcfile);
    let argv: Vec<_> = argv.iter().map(String::as_str).collect();
    terminal.spawn_async(
        vte::PtyFlags::DEFAULT,
        Some(&cwd),
        &argv,
        &[&session_env, "TERM=xterm-256color", "COLORTERM=truecolor"],
        glib::SpawnFlags::DEFAULT,
        || {},
        10000,
        None::<&gio::Cancellable>,
        move |result| {
            if let Some(tab) = weak.upgrade() {
                let mut tab = tab.borrow_mut();
                match result {
                    Ok(pid) => tab.child = Some(pid),
                    Err(e) => {
                        tab.alive = false;
                        tab.status.set_text(&format!("Bash could not start: {e}"));
                    }
                }
            }
        },
    );
    let weak = Rc::downgrade(&tab);
    glib::timeout_add_local(Duration::from_millis(60), move || {
        let Some(tab) = weak.upgrade() else {
            return glib::ControlFlow::Break;
        };
        let mut tab = tab.borrow_mut();
        if !tab.alive {
            return glib::ControlFlow::Break;
        }
        tab.poll(&requests);
        glib::ControlFlow::Continue
    });
    terminal.grab_focus();
    Ok(tab)
}

fn apply_terminal_theme(terminal: &vte::Terminal, theme: &crate::theme::Theme) {
    let color = |value: &str| gdk::RGBA::parse(value).expect("bundled theme color");
    let palette: Vec<_> = theme.palette.iter().map(|c| color(c)).collect();
    terminal.set_colors(
        Some(&color(&theme.foreground)),
        Some(&color(&theme.background)),
        &palette.iter().collect::<Vec<_>>(),
    );
    terminal.set_color_cursor(Some(&color(&theme.cursor)));
    terminal.set_color_cursor_foreground(Some(&color(&theme.background)));
    terminal.set_color_highlight(Some(&color(&theme.selection)));
    terminal.set_color_highlight_foreground(Some(&color(&theme.foreground)));
}
fn install_icon() {
    let resource = gio::Resource::from_data(&glib::Bytes::from_static(include_bytes!(concat!(
        env!("OUT_DIR"),
        "/cayman.gresource"
    ))))
    .expect("bundled icon resource");
    gio::resources_register(&resource);
    if let Some(display) = gdk::Display::default() {
        gtk::IconTheme::for_display(&display).add_resource_path("/io/cayman/Terminal/icons");
    }
    gtk::Window::set_default_icon_name("io.cayman.Terminal");
}

pub fn run(model: PathBuf, disabled: bool, options: crate::settings::Settings) {
    let app = gtk::Application::builder()
        .application_id("io.cayman.Terminal")
        .flags(gio::ApplicationFlags::NON_UNIQUE)
        .build();
    app.connect_activate(move |app| {
        install_icon();
        let settings = crate::theme::settings_path().ok();
        let initial =
            crate::theme::find(&options.theme).unwrap_or_else(crate::theme::default_theme);
        let selected = Rc::new(Cell::new(initial));
        let css = gtk::CssProvider::new();
        css.load_from_data(&initial.css_with_font(options.font_size));
        if let Some(display) = gdk::Display::default() {
            gtk::style_context_add_provider_for_display(
                &display,
                &css,
                gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
            );
        }
        let worker = worker::spawn(model.clone(), disabled, options.clone());
        let requests = worker.requests;
        let tabs: Rc<RefCell<Vec<Rc<RefCell<Tab>>>>> = Rc::new(RefCell::new(Vec::new()));
        let notebook = gtk::Notebook::new();
        notebook.set_scrollable(true);
        notebook.set_vexpand(true);
        let add = gtk::Button::from_icon_name("list-add-symbolic");
        add.add_css_class("flat");
        add.set_tooltip_text(Some("New tab (Ctrl+Shift+T)"));
        let menu_model = gio::Menu::new();
        menu_model.append(Some("New Tab"), Some("win.new-tab"));
        menu_model.append(Some("Close Tab"), Some("win.close-tab"));
        menu_model.append(Some("Show AI Pane"), Some("win.show-ai"));
        menu_model.append(Some("Enable AI"), Some("win.enable-ai"));
        menu_model.append(Some("Settings…"), Some("win.settings"));
        let theme_menu = gio::Menu::new();
        for theme in crate::theme::all() {
            let item = gio::MenuItem::new(Some(&theme.name), None);
            item.set_action_and_target_value(Some("win.theme"), Some(&theme.id.to_variant()));
            theme_menu.append_item(&item);
        }
        menu_model.append_submenu(Some("Theme"), &theme_menu);
        let menu = gtk::MenuButton::builder()
            .icon_name("open-menu-symbolic")
            .menu_model(&menu_model)
            .build();
        menu.add_css_class("flat");
        let controls = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        controls.append(&add);
        controls.append(&menu);
        notebook.set_action_widget(&controls, gtk::PackType::End);
        let window = gtk::ApplicationWindow::builder()
            .application(app)
            .title("cAIman Terminal")
            .default_width(1200)
            .default_height(760)
            .child(&notebook)
            .build();
        window.set_icon_name(Some("io.cayman.Terminal"));
        let theme_action = gio::SimpleAction::new_stateful(
            "theme",
            Some(glib::VariantTy::STRING),
            &initial.id.to_variant(),
        );
        let theme_font = options.font_size;
        let theme_tabs = tabs.clone();
        let theme_css = css.clone();
        let theme_selected = selected.clone();
        theme_action.connect_activate(move |action, value| {
            let Some(theme) = value.and_then(|v| v.str()).and_then(crate::theme::find) else {
                return;
            };
            theme_css.load_from_data(&theme.css_with_font(theme_font));
            for tab in theme_tabs.borrow().iter() {
                apply_terminal_theme(&tab.borrow().terminal, theme);
            }
            theme_selected.set(theme);
            action.set_state(&theme.id.to_variant());
            if let Some(path) = &settings {
                if let Err(e) = crate::theme::save(path, &theme.id) {
                    eprintln!("Theme applied, but could not save preference: {e}");
                }
            }
        });
        window.add_action(&theme_action);
        let enabled = Rc::new(Cell::new(!disabled));
        let pane_visible = Rc::new(Cell::new(options.show_ai));
        let model_status = Rc::new(RefCell::new(
            if disabled { "Off." } else { "Loading.." }.to_string(),
        ));
        let next_id = Rc::new(Cell::new(1u64));
        let create = {
            let options = options.clone();
            let tabs = tabs.clone();
            let book = notebook.clone();
            let requests = requests.clone();
            let next_id = next_id.clone();
            let status = model_status.clone();
            let pane_visible = pane_visible.clone();
            let enabled = enabled.clone();
            let selected = selected.clone();
            move || {
                let id = next_id.get();
                next_id.set(id + 1);
                match new_tab(&book, id, requests.clone(), enabled.get(), &options) {
                    Ok(tab) => {
                        apply_terminal_theme(&tab.borrow().terminal, selected.get());
                        let show = enabled.get() && pane_visible.get();
                        tab.borrow().pane.set_reveal_child(show);
                        tab.borrow().pane.set_visible(show);
                        let current_status = status.borrow();
                        tab.borrow().assistant.set_text(if enabled.get() {
                            &current_status
                        } else {
                            "Off."
                        });
                        tabs.borrow_mut().push(tab);
                    }
                    Err(e) => eprintln!("Could not create terminal: {e}"),
                }
            }
        };
        let create = Rc::new(create);
        create();
        let create_button = create.clone();
        add.connect_clicked(move |_| create_button());
        let new_action = gio::SimpleAction::new("new-tab", None);
        new_action.connect_activate(move |_, _| create());
        window.add_action(&new_action);
        app.set_accels_for_action("win.new-tab", &["<Control><Shift>t"]);
        let close_action = gio::SimpleAction::new("close-tab", None);
        let book = notebook.clone();
        close_action.connect_activate(move |_, _| {
            if let Some(page) = book.nth_page(book.current_page()) {
                if let Some(title) = book.tab_label(&page) {
                    if let Some(button) = title
                        .last_child()
                        .and_then(|w| w.downcast::<gtk::Button>().ok())
                    {
                        button.emit_clicked();
                    }
                }
            }
        });
        window.add_action(&close_action);
        app.set_accels_for_action("win.close-tab", &["<Control><Shift>w"]);
        for (name, offset, accelerators) in [
            ("previous-tab", -1, vec!["<Control>Page_Up", "<Shift>Left"]),
            ("next-tab", 1, vec!["<Control>Page_Down", "<Shift>Right"]),
        ] {
            let action = gio::SimpleAction::new(name, None);
            let book = notebook.clone();
            action.connect_activate(move |_, _| {
                let count = book.n_pages() as i32;
                if count > 0 {
                    let page = (book.current_page().unwrap_or(0) as i32 + offset).rem_euclid(count);
                    book.set_current_page(Some(page as u32));
                    if let Some(child) = book.nth_page(Some(page as u32)) {
                        child.child_focus(gtk::DirectionType::TabForward);
                    }
                }
            });
            window.add_action(&action);
            app.set_accels_for_action(&format!("win.{name}"), &accelerators);
        }
        let toggle = gio::SimpleAction::new_stateful(
            "show-ai",
            None,
            &(!disabled && options.show_ai).to_variant(),
        );
        toggle.set_enabled(!disabled);
        let pane_tabs = tabs.clone();
        let visible = pane_visible.clone();
        toggle.connect_activate(move |action, _| {
            let show = !visible.get();
            visible.set(show);
            action.set_state(&show.to_variant());
            for tab in pane_tabs.borrow().iter() {
                tab.borrow().pane.set_reveal_child(show);
                tab.borrow().pane.set_visible(show);
            }
        });
        window.add_action(&toggle);
        app.set_accels_for_action("win.show-ai", &["<Control><Shift>a"]);
        let enable_action =
            gio::SimpleAction::new_stateful("enable-ai", None, &(!disabled).to_variant());
        enable_action.set_enabled(!disabled);
        let enable_tabs = tabs.clone();
        let ai_enabled = enabled.clone();
        let status = model_status.clone();
        let show_action = toggle.clone();
        let visibility = pane_visible.clone();
        enable_action.connect_activate(move |action, _| {
            let on = !ai_enabled.get();
            ai_enabled.set(on);
            action.set_state(&on.to_variant());
            let show = on && visibility.get();
            show_action.set_enabled(on);
            show_action.set_state(&show.to_variant());
            for tab in enable_tabs.borrow().iter() {
                let mut tab = tab.borrow_mut();
                tab.enabled = on;
                tab.pane.set_reveal_child(show);
                tab.pane.set_visible(show);
                tab.invalidate();
                let current_status = status.borrow();
                tab.assistant
                    .set_text(if on { &current_status } else { "Off." });
            }
        });
        window.add_action(&enable_action);
        let settings_action = gio::SimpleAction::new("settings", None);
        let weak = window.downgrade();
        let active_model = model.clone();
        settings_action.connect_activate(move |_, _| {
            let Some(parent) = weak.upgrade() else {
                return;
            };
            let result = crate::settings::path()
                .and_then(|path| crate::settings::load(&path).map(|settings| (path, settings)));
            match result {
                Ok((path, settings)) => {
                    let weak = parent.downgrade();
                    crate::settings_ui::show(
                        &parent,
                        settings,
                        path,
                        active_model.clone(),
                        move |saved| {
                            if let Some(parent) = weak.upgrade() {
                                if !saved.ai_enabled {
                                    if let Some(action) = parent.lookup_action("enable-ai") {
                                        if action.state().and_then(|v| v.get::<bool>())
                                            == Some(true)
                                        {
                                            action.activate(None);
                                        }
                                    }
                                }
                                gio::prelude::ActionGroupExt::activate_action(
                                    &parent,
                                    "theme",
                                    Some(&saved.theme.to_variant()),
                                );
                            }
                        },
                    );
                }
                Err(error) => eprintln!("Could not open settings: {error}"),
            }
        });
        window.add_action(&settings_action);
        app.set_accels_for_action("win.settings", &["<Control>comma"]);
        let weak_window = window.downgrade();
        glib::timeout_add_local(Duration::from_millis(60), move || {
            if weak_window.upgrade().is_none() {
                return glib::ControlFlow::Break;
            }
            tabs.borrow_mut().retain(|tab| !tab.borrow().closed);
            while let Ok(event) = worker.events.try_recv() {
                match event {
                    Event::Status(status) => {
                        let text = if status.starts_with("Local AI ready") {
                            "Ready..".to_string()
                        } else if status.starts_with("Loading") {
                            "Loading..".to_string()
                        } else if disabled {
                            "Off.".to_string()
                        } else {
                            status
                        };
                        *model_status.borrow_mut() = text.clone();
                        for tab in tabs.borrow().iter() {
                            let tab = tab.borrow();
                            if tab.enabled && tab.assistant.current_text() == "Loading.." {
                                tab.assistant.set_text(&text);
                            }
                        }
                    }
                    Event::Completed {
                        id,
                        ticket,
                        passive,
                        result,
                    } => {
                        let tab = tabs
                            .borrow()
                            .iter()
                            .find(|tab| tab.borrow().session.id == id)
                            .cloned();
                        let Some(tab) = tab else {
                            continue;
                        };
                        let mut tab = tab.borrow_mut();
                        if !tab.enabled
                            || !tab.alive
                            || ticket != tab.cancellation.load(Ordering::Relaxed)
                        {
                            continue;
                        }
                        tab.activity.set_text("ai");
                        tab.pending = None;
                        tab.ghost.set_text("");
                        match result {
                            Ok(answer) => {
                                let mut message = answer
                                    .response
                                    .explanation
                                    .clone()
                                    .or(answer.response.question.clone())
                                    .unwrap_or_default();
                                if let Some(plan) = &answer.response.plan {
                                    message.push_str(&format!("\n\n{}", plan.join("\n")));
                                }
                                if let Some(v) = answer.validation {
                                    let Some(binding) = v.binding().cloned() else {
                                        continue;
                                    };
                                    if passive || !binding.matches(&tab.session) {
                                        continue;
                                    }
                                    message.push_str(&format!("\n\n$ {}", v.command));
                                    if v.risk != crate::host::Risk::Normal {
                                        message
                                            .push_str(&format!("\n\n{:?}: {}", v.risk, v.reason));
                                    }
                                    tab.ghost.set_text(&format!("{}  [Tab]", v.command));
                                    tab.ghost.set_visible(true);
                                    tab.suggested = Some(v.command.clone());
                                    tab.pending = Some(Suggestion {
                                        command: v.command,
                                        input: tab.session.input.clone(),
                                        ticket,
                                        binding,
                                    });
                                }
                                if !answer.source.is_empty() {
                                    message.push_str(&format!("\n\n{}", answer.source));
                                }
                                if !message.is_empty() {
                                    tab.assistant.response(&message, passive);
                                    tab.session.remember(format!("Assistant: {message}"));
                                }
                            }
                            Err(error) => {
                                tab.assistant.response(
                                    &format!(
                                        "{}\n\n{error}",
                                        if passive {
                                            "No verified suggestion."
                                        } else {
                                            "No command staged."
                                        }
                                    ),
                                    passive,
                                );
                            }
                        }
                    }
                }
            }
            glib::ControlFlow::Continue
        });
        window.present();
    });
    app.run_with_args::<&str>(&[]);
}

#[cfg(test)]
mod tests {
    use super::*;
    #[track_caller]
    fn pump_until(mut condition: impl FnMut() -> bool) {
        let deadline = Instant::now() + Duration::from_secs(8);
        while !condition() {
            assert!(Instant::now() < deadline, "GTK/Bash event timed out");
            while glib::MainContext::default().pending() {
                glib::MainContext::default().iteration(false);
            }
            std::thread::sleep(Duration::from_millis(10));
        }
    }
    #[test]
    #[ignore = "requires a graphical display; starts a real Bash PTY"]
    fn disabled_ai_hides_pane() {
        gtk::init().unwrap();
        let book = gtk::Notebook::new();
        let (tx, _rx) = std::sync::mpsc::sync_channel(2);
        let tab = new_tab(&book, 1, tx, false, &crate::settings::Settings::default()).unwrap();
        assert!(!tab.borrow().pane.reveals_child());
        assert!(!tab.borrow().pane.is_visible());
    }

    #[test]
    #[ignore = "requires a graphical display; runs a real Bash PTY"]
    fn desktop_flow() {
        gtk::init().unwrap();
        install_icon();
        assert!(
            gtk::IconTheme::for_display(&gdk::Display::default().unwrap())
                .has_icon("io.cayman.Terminal")
        );
        let css = gtk::CssProvider::new();
        let css_errors = Rc::new(RefCell::new(Vec::new()));
        let errors = css_errors.clone();
        css.connect_parsing_error(move |_, _, error| errors.borrow_mut().push(error.to_string()));
        css.load_from_data(&crate::theme::default_theme().css());
        gtk::style_context_add_provider_for_display(
            &gdk::Display::default().unwrap(),
            &css,
            gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
        );
        let book = gtk::Notebook::new();
        let window = gtk::Window::builder()
            .title("cAIman Terminal · verification")
            .default_width(1200)
            .default_height(760)
            .child(&book)
            .build();
        let (tx, rx) = std::sync::mpsc::sync_channel(2);
        let one = new_tab(
            &book,
            1,
            tx.clone(),
            true,
            &crate::settings::Settings::default(),
        )
        .unwrap();
        let two = new_tab(&book, 2, tx, true, &crate::settings::Settings::default()).unwrap();
        window.present();
        pump_until(|| one.borrow().session.at_prompt && two.borrow().session.at_prompt);
        book.set_current_page(Some(0));
        if std::env::var_os("CAYMAN_TEST_X11_KEYS").is_some() {
            one.borrow().terminal.grab_focus();
            let settle = Instant::now() + Duration::from_millis(100);
            pump_until(|| Instant::now() >= settle);
            let status = std::process::Command::new("python3")
                .arg(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/tests/type_into_test_window.py"
                ))
                .status()
                .unwrap();
            assert!(status.success());
            let mut request = None;
            pump_until(|| {
                request = rx.try_recv().ok();
                request.is_some()
            });
            let request = request.unwrap();
            assert_eq!(request.text, "find");
            assert_eq!(request.session.input, "find");
            let answer =
                worker::process(&request, |_| panic!("bare find must not need inference")).unwrap();
            assert!(
                answer.validation.is_none(),
                "Passive find advice cannot stage"
            );
            one.borrow().terminal.feed_child(b"\x15");
            // Confirm the buffer is empty before continuing the other PTY checks.
            one.borrow_mut().invalidate();
            pump_until(|| one.borrow().session.input.is_empty());
            one.borrow().assistant.set_text("Previous find advice");
            let started = Instant::now();
            assert!(std::process::Command::new("python3")
                .arg(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/tests/type_into_test_window.py"
                ))
                .arg("ps -")
                .status()
                .unwrap()
                .success());
            let mut flag_request = None;
            pump_until(|| {
                flag_request = rx.try_recv().ok();
                flag_request.is_some()
            });
            let elapsed = started.elapsed();
            assert!(
                elapsed < Duration::from_millis(650),
                "idle trigger took {elapsed:?}"
            );
            assert_eq!(one.borrow().assistant.text(), "Ready..");
            let flag_request = flag_request.unwrap();
            assert_eq!(flag_request.text, "ps -");
            let answer =
                worker::process(&flag_request, |_| panic!("flag help must not infer")).unwrap();
            assert!(answer
                .response
                .explanation
                .unwrap()
                .contains("all processes"));
            assert!(answer.validation.is_none());
            println!("Real ps - keys to idle request: {elapsed:?}");
            one.borrow().terminal.feed_child(b"\x15");
            one.borrow_mut().invalidate();
            pump_until(|| one.borrow().session.input.is_empty());
        }
        // A question about terminal output must carry the real VTE text and
        // shell result, even if the AI pane has unrelated previous advice.
        one.borrow()
            .terminal
            .feed_child(b"printf 'terminal-context-marker\\n'\r");
        pump_until(|| {
            one.borrow()
                .session
                .journal
                .back()
                .is_some_and(|r| r.command.contains("terminal-context-marker"))
        });
        while rx.try_recv().is_ok() {}
        one.borrow()
            .assistant
            .set_text("Unrelated old assistant advice");
        one.borrow()
            .terminal
            .feed_child(b"@ what does this output mean?\r");
        let mut context_request = None;
        pump_until(|| {
            if let Ok(request) = rx.try_recv() {
                if !request.passive {
                    context_request = Some(request);
                }
            }
            context_request.is_some()
        });
        let context_request = context_request.unwrap();
        assert!(context_request
            .session
            .terminal_text
            .contains("terminal-context-marker"));
        assert!(!context_request
            .session
            .terminal_text
            .contains("Unrelated old assistant advice"));
        assert!(context_request.session.at_prompt);
        assert_eq!(context_request.session.journal.back().unwrap().exit_code, 0);
        assert!(worker::build_prompt(&context_request, "").contains("terminal-context-marker"));
        assert!(two.borrow().session.terminal_text.is_empty());
        pump_until(|| one.borrow().session.at_prompt);
        let test_dir = tempfile::tempdir().unwrap();
        let marker = test_dir.path().join("executed-only-after-enter");
        let command = format!("touch {}", marker.display());
        one.borrow()
            .terminal
            .feed_child(format!("@ {command}\r").as_bytes());
        pump_until(|| rx.try_recv().is_ok());
        pump_until(|| one.borrow().session.at_prompt);
        assert!(!marker.exists(), "@ request must never execute");
        assert!(one
            .borrow()
            .assistant
            .text()
            .contains(&format!("@ {command}")));
        assert!(!two.borrow().assistant.text().contains(&command));
        {
            let mut tab = one.borrow_mut();
            tab.assistant
                .response("The command is ready to review.", false);
            tab.invalidate();
            tab.assistant.set_text("Temporary flag guidance");
            tab.invalidate();
            let transcript = tab.assistant.text();
            assert!(transcript.contains(&format!("@ {command}")));
            assert!(transcript.contains("The command is ready to review."));
            assert!(!transcript.contains("Temporary flag guidance"));
        }
        // Explicit messages remain visible even when no worker can answer.
        {
            let mut tab = two.borrow_mut();
            let (unavailable_tx, unavailable_rx) = std::sync::mpsc::sync_channel(1);
            drop(unavailable_rx);
            tab.request("explain this error".into(), false, &unavailable_tx);
            assert!(tab
                .assistant
                .text()
                .contains("@ explain this error\n\nAI unavailable."));
            tab.enabled = false;
            tab.request("help with find".into(), false, &unavailable_tx);
            assert!(tab.assistant.text().contains("@ help with find\n\nOff."));
            assert!(tab.assistant.text().contains("@ explain this error"));
            tab.enabled = true;
            assert!(!one.borrow().assistant.text().contains("@ help with find"));
        }
        {
            let mut tab = one.borrow_mut();
            let ticket = tab.cancellation.load(Ordering::Relaxed);
            tab.pending = Some(Suggestion {
                command: command.clone(),
                input: String::new(),
                ticket,
                binding: crate::context::ContextBinding::capture(&tab.session),
            });
            assert!(tab.accept());
        }
        pump_until(|| one.borrow().session.input == command);
        assert!(!marker.exists(), "staging must never execute");
        assert!(two.borrow().session.input.is_empty());
        assert!(two.borrow().session.journal.is_empty());
        // This byte represents the user's separate Enter action in the test.
        one.borrow().terminal.feed_child(b"\r");
        pump_until(|| {
            marker.exists()
                && one.borrow().session.at_prompt
                && one
                    .borrow()
                    .session
                    .journal
                    .back()
                    .is_some_and(|r| r.command == command)
        });
        assert!(one.borrow().session.journal.back().unwrap().ai_origin);
        let mut observed = None;
        pump_until(|| {
            observed = rx.try_recv().ok();
            observed.is_some()
        });
        let observed = observed.unwrap();
        assert!(observed.passive);
        assert_eq!(observed.text, "continue");
        assert_eq!(observed.session.journal.back().unwrap().exit_code, 0);
        one.borrow().terminal.feed_child(b"false\r");
        pump_until(|| {
            one.borrow()
                .session
                .journal
                .back()
                .is_some_and(|r| r.command == "false" && r.exit_code == 1)
        });
        let mut failure = None;
        pump_until(|| {
            failure = rx.try_recv().ok();
            failure.is_some()
        });
        let failure = failure.unwrap();
        assert!(failure.passive);
        assert_eq!(failure.text, "continue");
        assert_eq!(failure.session.journal.back().unwrap().command, "false");
        one.borrow()
            .terminal
            .feed_child(b"cayman_missing_binary_39281\r");
        let mut missing = None;
        pump_until(|| {
            missing = rx.try_recv().ok();
            missing.is_some()
        });
        let missing = missing.unwrap();
        let record = missing.session.journal.back().unwrap();
        assert_eq!(record.exit_code, 127);
        assert!(
            record.output.contains("command not found"),
            "{}",
            record.output
        );
        one.borrow().terminal.feed_child(b"clear\r");
        pump_until(|| {
            one.borrow()
                .session
                .journal
                .back()
                .is_some_and(|r| r.command == "clear")
        });
        assert!(one
            .borrow()
            .session
            .journal
            .iter()
            .any(|r| r.command == "false"));
        {
            let mut tab = one.borrow_mut();
            let ticket = tab.cancellation.load(Ordering::Relaxed);
            tab.pending = Some(Suggestion {
                command: "echo stale".into(),
                input: String::new(),
                ticket,
                binding: crate::context::ContextBinding::capture(&tab.session),
            });
            tab.invalidate();
            assert!(!tab.accept());
            tab.assistant.set_text("Ready..");
            assert_eq!(tab.assistant.current_text(), "Ready..");
            assert!(tab.assistant.text().contains(&format!("@ {command}")));
        }
        // Rapid edits are coalesced. No Readline widget is sent during typing;
        // one idle snapshot drives a passive request with the complete buffer.
        for byte in b"apt get update" {
            let mut tab = one.borrow_mut();
            tab.invalidate();
            tab.terminal.feed_child(&[*byte]);
        }
        assert!(one.borrow().snapshot_pending);
        assert!(one.borrow().session.input.is_empty());
        let mut idle = None;
        pump_until(|| {
            idle = rx.try_recv().ok();
            idle.is_some()
        });
        let idle = idle.unwrap();
        assert!(idle.passive);
        assert_eq!(idle.text, "apt get update");
        assert!(!one.borrow().snapshot_pending);
        assert!(!one.borrow().snapshot_waiting);
        assert!(two.borrow().session.journal.is_empty());
        // A full worker mailbox must not mark a passive request as delivered.
        let (busy_tx, busy_rx) = std::sync::mpsc::sync_channel(1);
        busy_tx.try_send(idle).unwrap();
        {
            let mut tab = one.borrow_mut();
            tab.invalidate();
            tab.request("update my system".into(), true, &busy_tx);
            let ticket = tab.cancellation.load(Ordering::Relaxed);
            assert_ne!(tab.passive_ticket, Some(ticket));
            busy_rx.try_recv().unwrap();
            tab.request("update my system".into(), true, &busy_tx);
            assert_eq!(tab.passive_ticket, Some(ticket));
        }
        // Clear the unfinished input without submitting it.
        one.borrow().terminal.feed_child(b"\x15");
        while rx.try_recv().is_ok() {}
        one.borrow()
            .terminal
            .feed_child(b"command /bin/sleep 0.3\r");
        pump_until(|| !one.borrow().session.at_prompt);
        assert!(
            one.borrow().session.remote,
            "Every running wrapper has unknown host identity"
        );
        one.borrow().terminal.feed(b"\x1b]133;A\x07");
        let (paused_tx, paused_rx) = std::sync::mpsc::sync_channel(1);
        one.borrow_mut().request("ls".into(), false, &paused_tx);
        assert!(paused_rx.try_recv().is_err());
        assert!(!one.borrow().session.at_prompt);
        pump_until(|| one.borrow().session.at_prompt);
        assert!(!one.borrow().session.remote);
        // Terminal escapes are display data, never authenticated shell events.
        let revision = one.borrow().session.revision;
        let cwd = one.borrow().session.cwd.clone();
        let clipboard = gdk::Display::default().unwrap().clipboard();
        clipboard.set_text("caiman-clipboard-sentinel");
        one.borrow()
            .terminal
            .feed(b"\x1b]133;A\x07\x1b]7;file://host/forged\x07\x1b]52;c;Zm9yZ2Vk\x07");
        let settled = Instant::now() + Duration::from_millis(100);
        pump_until(|| Instant::now() >= settled);
        assert_eq!(one.borrow().session.revision, revision);
        assert_eq!(one.borrow().session.cwd, cwd);
        let clipboard_text = Rc::new(RefCell::new(None));
        let result = clipboard_text.clone();
        clipboard.read_text_async(None::<&gio::Cancellable>, move |text| {
            *result.borrow_mut() = Some(text.unwrap().unwrap().to_string());
        });
        pump_until(|| clipboard_text.borrow().is_some());
        assert_eq!(
            clipboard_text.borrow().as_deref(),
            Some("caiman-clipboard-sentinel")
        );
        // Every palette updates both panes without replacing the running shell
        // or changing its context. Capture the actual widgets for visual review.
        one.borrow().terminal.feed(b"\r\n\x1b[31mred  \x1b[32mgreen  \x1b[33myellow  \x1b[34mblue  \x1b[35mmagenta  \x1b[36mcyan\x1b[0m\r\n");
        let journal_len = one.borrow().session.journal.len();
        for theme in crate::theme::all() {
            css.load_from_data(&theme.css());
            for tab in [&one, &two] {
                apply_terminal_theme(&tab.borrow().terminal, theme);
                assert_eq!(
                    tab.borrow().terminal.color_background_for_draw(),
                    gdk::RGBA::parse(&theme.background).unwrap()
                );
            }
            let settled = Instant::now() + Duration::from_millis(100);
            pump_until(|| Instant::now() >= settled);
            let mut node = None;
            book.queue_draw();
            pump_until(|| {
                let paintable = gtk::WidgetPaintable::new(Some(&book));
                let snapshot = gtk::Snapshot::new();
                paintable.snapshot(&snapshot, window.width() as f64, window.height() as f64);
                node = snapshot.to_node();
                node.is_some()
            });
            let node = node.unwrap();
            let renderer = gtk::gsk::Renderer::for_surface(&window.surface().unwrap()).unwrap();
            renderer
                .render_texture(&node, None)
                .save_to_png(format!("/tmp/cayman-theme-{}.png", theme.id))
                .unwrap();
            renderer.unrealize();
        }
        assert_eq!(one.borrow().session.journal.len(), journal_len);
        assert!(css_errors.borrow().is_empty(), "{:?}", css_errors.borrow());
        window.close();
    }
}
