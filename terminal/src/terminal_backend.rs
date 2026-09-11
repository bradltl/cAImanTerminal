//! The assistant reads a terminal surface through this contract, independent of
//! the widget library. Shell event parsing and staging remain separate contracts.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum IntegrationKey {
    Snapshot,
    Stage,
}
impl IntegrationKey {
    pub fn bytes(self) -> &'static [u8] {
        match self {
            Self::Snapshot => b"\x18\x07",
            Self::Stage => b"\x18s",
        }
    }
}
pub trait TerminalSurface {
    fn context_text(&self) -> String;
    fn send_integration_key(&self, key: IntegrationKey);
}
#[cfg(feature = "desktop")]
impl TerminalSurface for vte::Terminal {
    fn context_text(&self) -> String {
        use vte::prelude::*;
        let (_, row) = self.cursor_position();
        let (text, _) = self.text_range_format(
            vte::Format::Text,
            (row - 100).max(0),
            0,
            row + self.row_count(),
            -1,
        );
        text.as_deref().unwrap_or("").to_string()
    }
    fn send_integration_key(&self, key: IntegrationKey) {
        use vte::prelude::*;
        self.feed_child(key.bytes());
    }
}
