from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_adapter_sleep():
    with patch("ip_info.channel.adapter.time.sleep"):
        yield
