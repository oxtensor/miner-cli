import os
import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from types import ModuleType
from unittest.mock import patch


# The input helpers are deliberately testable without installing Bittensor or
# connecting to a chain. Provide minimal import-time stand-ins when optional
# runtime dependencies are absent.
try:
    import bittensor  # noqa: F401
except ModuleNotFoundError:
    bittensor = ModuleType("bittensor")
    async_subtensor = ModuleType("bittensor.core.async_subtensor")
    stake_info = ModuleType("bittensor.core.chain_data.stake_info")
    balance = ModuleType("bittensor.utils.balance")

    async_subtensor.AsyncSubtensor = object
    stake_info.StakeInfo = object
    balance.Balance = object

    sys.modules.update(
        {
            "bittensor": bittensor,
            "bittensor.core": ModuleType("bittensor.core"),
            "bittensor.core.async_subtensor": async_subtensor,
            "bittensor.core.chain_data": ModuleType("bittensor.core.chain_data"),
            "bittensor.core.chain_data.stake_info": stake_info,
            "bittensor.utils": ModuleType("bittensor.utils"),
            "bittensor.utils.balance": balance,
        }
    )

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv

import unstake


class RetryLimitTests(unittest.TestCase):
    def test_default_and_positive_limit(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(unstake._max_retry_limit_from_env(), 10)
        with patch.dict(os.environ, {"MAX_RETRY_COUNT": " 7 "}):
            self.assertEqual(unstake._max_retry_limit_from_env(), 7)

    def test_nonpositive_limit_means_unlimited(self):
        for raw in ("0", "-1"):
            with self.subTest(raw=raw), patch.dict(os.environ, {"MAX_RETRY_COUNT": raw}):
                self.assertIsNone(unstake._max_retry_limit_from_env())

    def test_invalid_limit_warns_and_uses_default(self):
        stderr = StringIO()
        with patch.dict(os.environ, {"MAX_RETRY_COUNT": "many"}), redirect_stderr(stderr):
            self.assertEqual(unstake._max_retry_limit_from_env(), 10)
        self.assertIn("MAX_RETRY_COUNT must be an integer", stderr.getvalue())


class NetuidTests(unittest.TestCase):
    def test_accepts_supported_range(self):
        for raw, expected in (("0", 0), (" 42 ", 42), ("128", 128)):
            with self.subTest(raw=raw):
                self.assertEqual(unstake._parse_netuid(raw), expected)

    def test_rejects_invalid_or_out_of_range_values(self):
        for raw in ("", "1.5", "abc", "-1", "129"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                unstake._parse_netuid(raw)


class LimitPriceTests(unittest.TestCase):
    def test_empty_input_means_market_price(self):
        self.assertIsNone(unstake._parse_limit_price(""))
        self.assertIsNone(unstake._parse_limit_price("   "))

    def test_accepts_nonnegative_finite_prices(self):
        self.assertEqual(unstake._parse_limit_price("0"), 0.0)
        self.assertEqual(unstake._parse_limit_price(" 1.25 "), 1.25)

    def test_rejects_negative_nonfinite_and_invalid_prices(self):
        for raw in ("-0.01", "nan", "inf", "-inf", "abc"):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "non-negative finite number"):
                unstake._parse_limit_price(raw)


if __name__ == "__main__":
    unittest.main()
