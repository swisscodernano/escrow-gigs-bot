import types
import pytest

class _Msg:
    def __init__(self): self.last=None
    async def reply_text(self, text, **kwargs): self.last=text

class _Update:
    def __init__(self):
        self.effective_message=_Msg()
        self.message=self.effective_message
        self.effective_chat=types.SimpleNamespace(id=1)

class _Ctx:
    def __init__(self, args=None): self.args=args or []

@pytest.mark.asyncio
async def test_start_and_help():
    from _autostart import _start, _help
    u=_Update(); c=_Ctx()
    await _start(u,c); assert "Welcome to Escrow Gigs" in u.effective_message.last
    await _help(u,c);  assert "/newgig" in u.effective_message.last

@pytest.mark.asyncio
async def test_release_usage_hint_when_missing_args():
    from _autostart import _release
    u=_Update(); c=_Ctx(args=[])
    await _release(u,c)
    assert "Use: /release <order_id>" in u.effective_message.last
