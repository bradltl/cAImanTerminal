//! Settings is a separate window; the terminal workspace stays minimal.
use crate::settings::Settings;
use gtk::prelude::*;
use std::path::PathBuf;

fn page() -> gtk::Box {
    gtk::Box::builder()
        .orientation(gtk::Orientation::Vertical)
        .spacing(14)
        .margin_top(22)
        .margin_bottom(22)
        .margin_start(24)
        .margin_end(24)
        .build()
}
fn row(container: &gtk::Box, title: &str, widget: &impl IsA<gtk::Widget>) {
    let line = gtk::Box::new(gtk::Orientation::Horizontal, 18);
    let label = gtk::Label::builder()
        .label(title)
        .xalign(0.0)
        .hexpand(true)
        .build();
    line.append(&label);
    line.append(widget);
    container.append(&line);
}
fn note(container: &gtk::Box, text: &str) {
    container.append(
        &gtk::Label::builder()
            .label(text)
            .xalign(0.0)
            .wrap(true)
            .build(),
    );
}
fn spin(value: f64, min: f64, max: f64, step: f64) -> gtk::SpinButton {
    let spin = gtk::SpinButton::with_range(min, max, step);
    spin.set_value(value);
    spin
}
fn providers(items: &[crate::adapters::ProviderDescriptor], selected: &str) -> gtk::DropDown {
    let names: Vec<_> = items.iter().map(|item| item.name).collect();
    let dropdown = gtk::DropDown::from_strings(&names);
    dropdown.set_selected(
        items
            .iter()
            .position(|item| item.id == selected)
            .unwrap_or(0) as u32,
    );
    dropdown.set_sensitive(items.len() > 1);
    dropdown
}
pub fn show(
    parent: &gtk::ApplicationWindow,
    settings: Settings,
    path: PathBuf,
    active_model: PathBuf,
    saved: impl Fn(Settings) + 'static,
) -> gtk::Window {
    let window = gtk::Window::builder()
        .title("cAIman Settings")
        .transient_for(parent)
        .modal(true)
        .default_width(760)
        .default_height(660)
        .build();
    let root = gtk::Box::new(gtk::Orientation::Vertical, 0);
    let body = gtk::Box::new(gtk::Orientation::Horizontal, 0);
    body.set_vexpand(true);
    let stack = gtk::Stack::builder().hexpand(true).vexpand(true).build();
    let sidebar = gtk::StackSidebar::new();
    sidebar.set_stack(&stack);
    sidebar.set_size_request(170, -1);
    body.append(&sidebar);
    body.append(&stack);
    root.append(&body);

    let appearance = page();
    note(&appearance, "Appearance");
    let names: Vec<_> = crate::theme::all()
        .iter()
        .map(|t| t.name.as_str())
        .collect();
    let theme = gtk::DropDown::from_strings(&names);
    theme.set_selected(
        crate::theme::all()
            .iter()
            .position(|t| t.id == settings.theme)
            .unwrap_or(0) as u32,
    );
    row(&appearance, "Theme", &theme);
    let font = spin(settings.font_size as f64, 8.0, 32.0, 1.0);
    row(&appearance, "Font size (pt)", &font);
    let scrollback = spin(settings.scrollback as f64, 100.0, 100000.0, 100.0);
    row(&appearance, "Scrollback lines", &scrollback);
    note(
        &appearance,
        "Theme changes and disabling AI apply when saved. Other changes take effect when cAIman is relaunched.",
    );
    stack.add_titled(&appearance, Some("appearance"), "Appearance");

    let assistant = page();
    let enabled = gtk::CheckButton::with_label("Enable local AI");
    enabled.set_active(settings.ai_enabled);
    assistant.append(&enabled);
    let visible = gtk::CheckButton::with_label("Show AI pane on startup");
    visible.set_active(settings.show_ai);
    assistant.append(&visible);
    let delay = spin(settings.idle_ms as f64, 150.0, 5000.0, 50.0);
    row(&assistant, "Pause before help (ms)", &delay);
    note(&assistant, "Commands always require your Enter key. Context is kept within each tab and redacted before inference.");
    stack.add_titled(&assistant, Some("assistant"), "Assistant");

    let model = page();
    let backend = providers(crate::adapters::MODEL_BACKENDS, &settings.model_backend);
    row(&model, "Model backend", &backend);
    note(&model, &format!("Active model: {}", active_model.display()));
    note(
        &model,
        "Model file (leave empty to use the application default)",
    );
    let model_path = gtk::Entry::builder()
        .hexpand(true)
        .placeholder_text(crate::default_model())
        .build();
    if let Some(path) = &settings.model_path {
        model_path.set_text(&path.to_string_lossy());
    }
    model.append(&model_path);
    let browse = gtk::Button::with_label("Choose GGUF…");
    model.append(&browse);
    let entry = model_path.clone();
    let weak = window.downgrade();
    browse.connect_clicked(move |_| {
        let Some(parent) = weak.upgrade() else {
            return;
        };
        let chooser = gtk::FileChooserNative::new(
            Some("Choose local model"),
            Some(&parent),
            gtk::FileChooserAction::Open,
            Some("Choose"),
            Some("Cancel"),
        );
        let filter = gtk::FileFilter::new();
        filter.set_name(Some("GGUF models"));
        filter.add_pattern("*.gguf");
        chooser.add_filter(&filter);
        let entry = entry.clone();
        chooser.connect_response(move |chooser, response| {
            if response == gtk::ResponseType::Accept {
                if let Some(path) = chooser.file().and_then(|f| f.path()) {
                    entry.set_text(&path.to_string_lossy());
                }
            }
            chooser.destroy();
        });
        chooser.show();
    });
    let threads = spin(settings.inference.threads as f64, 1.0, 64.0, 1.0);
    let digest = gtk::Entry::builder()
        .placeholder_text("Trusted SHA-256; empty uses the bundled default digest")
        .text(settings.inference.model_sha256.as_deref().unwrap_or(""))
        .build();
    row(&model, "Model SHA-256", &digest);
    row(&model, "CPU threads", &threads);
    let context = spin(
        settings.inference.context_tokens as f64,
        2048.0,
        32768.0,
        1024.0,
    );
    row(&model, "Context tokens", &context);
    let output = spin(settings.inference.output_tokens as f64, 64.0, 2048.0, 64.0);
    row(&model, "Maximum response tokens", &output);
    let timeout = spin(settings.inference.timeout_seconds as f64, 5.0, 300.0, 5.0);
    row(&model, "Inference timeout (seconds)", &timeout);
    note(&model, "Choose a context size supported by your GGUF. Larger contexts and models use more memory. No models are downloaded automatically.");
    let model_scroll = gtk::ScrolledWindow::builder()
        .child(&model)
        .hscrollbar_policy(gtk::PolicyType::Never)
        .build();
    stack.add_titled(&model_scroll, Some("model"), "Model & runtime");

    let host = page();
    note(&host, "Operating system: automatically detected");
    note(&host, &crate::command_validation::Host::local().os);
    let terminal_backend = providers(
        crate::adapters::TERMINAL_BACKENDS,
        &settings.terminal_backend,
    );
    row(&host, "Terminal renderer", &terminal_backend);
    let shell = providers(crate::adapters::SHELL_INTEGRATIONS, &settings.shell);
    row(&host, "Shell integration", &shell);
    note(
        &host,
        &format!("Host adapter: {}", crate::platform::local().id()),
    );
    note(&host, "Command flags are checked against installed help. Cached help expires after five minutes and is refreshed when the executable changes. Unsupported command options are rejected.");
    note(&host, "Only implemented providers are available. Additional model backends, terminals, shells and operating systems can be added through the adapter registry.");
    note(&host, &format!("Settings file: {}", path.display()));
    stack.add_titled(&host, Some("host"), "Terminal & host");

    let footer = page();
    let status = gtk::Label::builder().xalign(0.0).wrap(true).build();
    footer.append(&status);
    let buttons = gtk::Box::new(gtk::Orientation::Horizontal, 12);
    buttons.set_halign(gtk::Align::End);
    let cancel = gtk::Button::with_label("Close");
    let save = gtk::Button::with_label("Save settings");
    save.add_css_class("suggested-action");
    buttons.append(&cancel);
    buttons.append(&save);
    footer.append(&buttons);
    root.append(&footer);
    let weak = window.downgrade();
    cancel.connect_clicked(move |_| {
        if let Some(window) = weak.upgrade() {
            window.close();
        }
    });
    save.connect_clicked(move |_| {
        let mut updated = settings.clone();
        updated.theme = crate::theme::all()[theme.selected() as usize].id.clone();
        updated.model_backend = crate::adapters::MODEL_BACKENDS[backend.selected() as usize]
            .id
            .into();
        updated.terminal_backend = crate::adapters::TERMINAL_BACKENDS
            [terminal_backend.selected() as usize]
            .id
            .into();
        updated.shell = crate::adapters::SHELL_INTEGRATIONS[shell.selected() as usize]
            .id
            .into();
        updated.font_size = font.value_as_int() as u32;
        updated.scrollback = scrollback.value_as_int() as u32;
        updated.ai_enabled = enabled.is_active();
        updated.show_ai = visible.is_active();
        updated.idle_ms = delay.value_as_int() as u64;
        let value = model_path.text();
        updated.model_path = if value.trim().is_empty() {
            None
        } else {
            Some(PathBuf::from(value.as_str()))
        };
        updated.inference.threads = threads.value_as_int();
        updated.inference.model_sha256 =
            (!digest.text().trim().is_empty()).then(|| digest.text().trim().to_string());
        updated.inference.context_tokens = context.value_as_int() as u32;
        updated.inference.output_tokens = output.value_as_int() as usize;
        updated.inference.timeout_seconds = timeout.value_as_int() as u64;
        if let Some(path) = &updated.model_path {
            if !path.is_file() {
                status.set_text("Choose an existing local GGUF file.");
                return;
            }
        }
        match crate::settings::save(&path, &updated) {
            Ok(()) => {
                saved(updated);
                status
                    .set_text("Saved. Theme applied. Relaunch cAIman to apply the other settings.");
            }
            Err(error) => status.set_text(&format!("Could not save: {error}")),
        }
    });
    window.set_child(Some(&root));
    window.present();
    window
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{cell::Cell, rc::Rc};
    fn descendants(root: &gtk::Widget) -> Vec<gtk::Widget> {
        let mut result = vec![root.clone()];
        let mut child = root.first_child();
        while let Some(widget) = child {
            result.extend(descendants(&widget));
            child = widget.next_sibling();
        }
        result
    }
    #[test]
    #[ignore = "requires a graphical display"]
    fn settings_window() {
        gtk::init().unwrap();
        let app = gtk::Application::builder()
            .application_id("io.cayman.SettingsTest")
            .build();
        app.register(None::<&gtk::gio::Cancellable>).unwrap();
        let parent = gtk::ApplicationWindow::builder().application(&app).build();
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("settings.json");
        let saved = Rc::new(Cell::new(false));
        let called = saved.clone();
        let window = show(
            &parent,
            Settings::default(),
            path.clone(),
            crate::default_model().into(),
            move |_| called.set(true),
        );
        let widgets = descendants(window.upcast_ref());
        let theme = widgets
            .iter()
            .find_map(|w| w.clone().downcast::<gtk::DropDown>().ok())
            .unwrap();
        theme.set_selected(2);
        let entry = widgets
            .iter()
            .find_map(|w| w.clone().downcast::<gtk::Entry>().ok())
            .unwrap();
        let button = widgets
            .iter()
            .filter_map(|w| w.clone().downcast::<gtk::Button>().ok())
            .find(|b| b.label().as_deref() == Some("Save settings"))
            .unwrap();
        entry.set_text("/not/a/real/model.gguf");
        button.emit_clicked();
        assert!(!path.exists());
        assert!(!saved.get());
        entry.set_text("");
        button.emit_clicked();
        assert!(saved.get());
        assert_eq!(crate::settings::load(&path).unwrap().theme, "nord");
        let until = std::time::Instant::now() + std::time::Duration::from_millis(250);
        while std::time::Instant::now() < until {
            while gtk::glib::MainContext::default().pending() {
                gtk::glib::MainContext::default().iteration(false);
            }
            std::thread::sleep(std::time::Duration::from_millis(10));
        }
        let paintable = gtk::WidgetPaintable::new(Some(&window));
        let snapshot = gtk::Snapshot::new();
        paintable.snapshot(&snapshot, window.width() as f64, window.height() as f64);
        let renderer = gtk::gsk::Renderer::for_surface(&window.surface().unwrap()).unwrap();
        renderer
            .render_texture(snapshot.to_node().unwrap(), None)
            .save_to_png("/tmp/cayman-settings.png")
            .unwrap();
        renderer.unrealize();
        window.close();
        parent.close();
    }
}
