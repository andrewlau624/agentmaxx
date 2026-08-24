#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_contract.py")
spec = importlib.util.spec_from_file_location("better_contract_impl", path)
better_contract = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_contract)

contract = better_contract.contract


class TestContractExtraction(unittest.TestCase):
    def test_contract_output(self):
        result = contract(path=".")
        self.assertIn("path", result)
        self.assertIn("routes", result)
        self.assertIn("schemas", result)

    def test_output_structure(self):
        result = contract(path=".", format="json")
        self.assertIn("route_count", result)
        self.assertIn("schema_count", result)


if __name__ == "__main__":
    unittest.main()
