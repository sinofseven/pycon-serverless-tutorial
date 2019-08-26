import pytest
import index


class TestHandler(object):
    @pytest.mark.parametrize(
        'error', [
            (TypeError),
            (ValueError),
            (KeyError)
        ]
    )
    def test_exception(self, monkeypatch, error):
        def dummy(*_, **__):
            raise error()
        monkeypatch.setattr(index, 'main', dummy)
        with pytest.raises(error):
            index.handler({}, None)

    def test_normal(self, monkeypatch):
        monkeypatch.setattr(index, 'main', lambda *_, **__: None)
        index.handler({}, None)
