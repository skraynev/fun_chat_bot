import pytest


class Test:
    def test_first(self):
        with pytest.raises(ValueError):
            raise ValueError
