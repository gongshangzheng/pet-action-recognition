"""Regression checks for observable composition/export invariants."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('svg_tools', Path(__file__).with_name('svg_tools.py'))
if spec is None or spec.loader is None:
    raise RuntimeError('找不到同目录下的 svg_tools.py')
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)

# 物理尺寸校验需要 PIL 与 pypdf；缺依赖时跳过该用例，不把环境差异当失败。
_HAVE_PIL = importlib.util.find_spec('PIL') is not None
_HAVE_PYPDF = importlib.util.find_spec('pypdf') is not None


class SvgTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def svg(self, name, content):
        p = self.root / name
        p.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 20 100 50">' + content + '</svg>')
        return p

    def test_colliding_ids_are_distinct_and_references_survive(self):
        self.svg('a.svg', '<defs><path id="glyph" d="M0 0H1"/></defs><use href="#glyph"/>')
        self.svg('b.svg', '<defs><path id="glyph" d="M0 0H2"/></defs><use href="#glyph"/>')
        p = self.root / 'layout.json'
        p.write_text(json.dumps({'width': 200, 'height': 100, 'title': 'test', 'items': [
            {'file': 'a.svg', 'x': 0, 'y': 0, 'width': 100},
            {'file': 'b.svg', 'x': 100, 'y': 0, 'width': 100}]}))
        output = self.root / 'result.svg'
        tools.compose(SimpleNamespace(spec=str(p), output=str(output)))
        root = tools.load(output)
        uses = root.findall('.//{' + tools.SVG + '}use')
        self.assertEqual({n.get('href') for n in uses}, {'#part0_glyph', '#part1_glyph'})
        self.assertEqual(root.findall('{' + tools.SVG + '}svg')[0].get('viewBox'), '10 20 100 50')

    def test_missing_reference_and_external_asset_fail(self):
        for content in ['<use href="#missing"/>', '<image href="https://example.com/image.png"/>']:
            with self.assertRaises(ValueError):
                tools.load(self.svg('bad.svg', content))

    def test_outputs_never_overwrite(self):
        path = self.root / 'existing.svg'
        path.write_bytes(b'original')
        with self.assertRaises(FileExistsError):
            tools.write_new(path, b'replacement')
        self.assertEqual(path.read_bytes(), b'original')

    def test_outside_placement_fails(self):
        self.svg('a.svg', '<path d="M0 0H1"/>')
        p = self.root / 'layout.json'
        p.write_text(json.dumps({'width': 100, 'height': 50, 'title': 'test', 'items': [
            {'file': 'a.svg', 'x': 1, 'width': 100}]}))
        with self.assertRaises(ValueError):
            tools.compose(SimpleNamespace(spec=str(p), output=str(self.root / 'bad.svg')))
        self.assertFalse((self.root / 'bad.svg').exists())

    def test_duplicate_ids_fail(self):
        with self.assertRaises(ValueError):
            tools.load(self.svg('dup.svg', '<path id="x"/><path id="x"/>'))

    @unittest.skipUnless(_HAVE_PIL and _HAVE_PYPDF, 'PIL / pypdf 未安装，跳过物理尺寸校验')
    def test_physical_export(self):
        from PIL import Image
        from pypdf import PdfReader  # type: ignore[import-not-found]
        source = self.svg('drawing.svg', '<rect x="10" y="20" width="100" height="50" fill="blue"/>')
        for ext in ['png', 'pdf']:
            tools.export(SimpleNamespace(input=str(source), output=str(self.root / ('result.'+ext)),
                                         backend='auto', dpi=300, width_mm=89))
        with Image.open(self.root / 'result.png') as image:
            self.assertAlmostEqual(image.width, 89 / 25.4 * 300, delta=1)
        box = PdfReader(self.root / 'result.pdf').pages[0].mediabox
        self.assertAlmostEqual(float(box.width), 89 / 25.4 * 72, places=2)


if __name__ == '__main__':
    unittest.main()
