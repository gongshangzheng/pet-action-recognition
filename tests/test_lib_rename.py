"""Import contracts for the repository's reusable library package."""

import importlib
import unittest
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import patch


class LibraryImportTest(unittest.TestCase):
    def test_schema_and_registry_resolve_from_repository(self):
        library = importlib.import_module("lib")
        root = Path(__file__).resolve().parents[1]
        self.assertIsNotNone(library.__file__)
        self.assertEqual(Path(str(library.__file__)).resolve(), root / "lib" / "__init__.py")
        self.assertTrue(importlib.import_module("lib.schemas").Detection)
        self.assertTrue(callable(importlib.import_module("lib.registry").create))

    def test_registry_dispatches_each_implementation_under_lib(self):
        registry = importlib.import_module("lib.registry")
        targets = {
            "detector": ("grounding_dino",),
            "tracker": ("byte_track", "oc_sort", "bot_sort", "deep_sort"),
            "keypoints": ("superanimal", "vitpose_ap10k"),
        }

        class Dispatched(Exception):
            pass

        for kind, names in targets.items():
            for name in names:
                with self.subTest(kind=kind, name=name):
                    def probe(module):
                        self.assertEqual(module.split(".")[0], "lib")
                        self.assertIsNotNone(find_spec(module))
                        raise Dispatched

                    with patch.object(registry.importlib, "import_module", side_effect=probe), self.assertRaises(Dispatched):
                        registry.create(kind, name)


if __name__ == "__main__":
    unittest.main()
