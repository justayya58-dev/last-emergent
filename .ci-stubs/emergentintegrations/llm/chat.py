"""Deterministic test double for the private Emergent LLM SDK; CI only."""
import json
from types import SimpleNamespace

class UserMessage:
    def __init__(self, text="", file_contents=None):
        self.text = text
        self.file_contents = file_contents or []
class FileContentWithMimeType:
    def __init__(self, mime_type="", file_path=""):
        self.mime_type, self.file_path = mime_type, file_path
class TextDelta:
    def __init__(self, content=""): self.content = content
class StreamDone:
    def __init__(self, content=""): self.content = content
class ToolCallReady:
    def __init__(self, tool_call=None): self.tool_call = tool_call
class LlmChat:
    def __init__(self, *args, **kwargs): self._tool_results = []
    def with_model(self, *args, **kwargs): return self
    def with_tools(self, *args, **kwargs): return self
    def with_params(self, *args, **kwargs): return self
    def add_tool_result(self, tool_call_id, result): self._tool_results.append((tool_call_id, result))
    async def stream_message(self, turn):
        if turn is None:
            answer = "Draft laporan sudah disiapkan untuk konfirmasi. Ringkasan piutang saat ini: Rp 0 berdasarkan data uji."
            yield TextDelta(answer)
            yield StreamDone(answer)
            return
        prompt = getattr(turn, "text", "").lower()
        if "draft laporan" in prompt or "buatkan draft laporan" in prompt:
            args = {"title":"Draft Laporan Keuangan (CI)","period_start":"2026-01-01","period_end":"2026-12-31","summary_focus":"Ringkasan uji CI"}
            yield ToolCallReady(SimpleNamespace(id="ci-report-tool",name="propose_draft_report",arguments=json.dumps(args)))
            return
        answer = "Berdasarkan data uji, total piutang adalah Rp 0. Periksa invoice terbuka sebelum penagihan."
        yield TextDelta(answer)
        yield StreamDone(answer)
