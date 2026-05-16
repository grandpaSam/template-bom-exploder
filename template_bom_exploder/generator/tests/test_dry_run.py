import unittest
from unittest.mock import patch
from template_bom_exploder.generator.dry_run import run_dry_run

class TestRunDryRun(unittest.TestCase):

    def setUp(self):
        # Shared mock data
        self.template_bom_name = 'BOM-ROOT-TEMPLATE'
        self.root_item_code = 'ROOT-TEMPLATE-ITEM'

        # Mocking the item database/registry
        self.item_map = {
            'ROOT-TEMPLATE-ITEM': {'item_code': 'ROOT-TEMPLATE-ITEM', 'variant_of': None, 'has_variants': True},
            'SUB-ASSEMBLY-TEMPLATE': {'item_code': 'SUB-ASSEMBLY-TEMPLATE', 'variant_of': None, 'has_variants': True},
            'LEAF-ITEM': {'item_code': 'LEAF-ITEM', 'variant_of': None, 'has_variants': False},
        }

        self.attr_map = {
            'ROOT-TEMPLATE-ITEM': ['Color-ASR'],
            'SUB-ASSEMBLY-TEMPLATE': ['Color-ASR'],
        }

        self.variants_map = {
            'ROOT-TEMPLATE-ITEM': [
                {'item_code': 'ROOT-VARIANT-BLACK', 'attributes': {'Color-ASR': 'Black'}},
                {'item_code': 'ROOT-VARIANT-RED', 'attributes': {'Color-ASR': 'Red'}},
            ]
        }

        self.bom_items_map = {
            'BOM-ROOT-TEMPLATE': [
                {'item_code': 'ROOT-TEMPLATE-ITEM', 'qty': 1, 'uom': 'Nos'},
                {'item_code': 'SUB-ASSEMBLY-TEMPLATE', 'qty': 1, 'uom': 'Nos'},
            ],
            'BOM-SUB-ASSEMBLY': [
                {'item_code': 'LEAF-ITEM', 'qty': 5, 'uom': 'Nos'},
            ]
        }

        self.template_bom_map = {
            'SUB-ASSEMBLY-TEMPLATE': 'BOM-SUB-ASSEMBLY',
        }

        self.compatibility_map = {}

    def _make_mocks(self):
        """Helper to create all required dependency injection functions."""
        get_bom_items_fn = lambda name: self.bom_items_map.get(name, [])
        get_template_bom_fn = lambda item: self.template_bom_map.get(item)
        get_item_fn = lambda item: self.item_map.get(item, {})
        get_variant_attributes_fn = lambda item: self.attr_map.get(item, [])
        get_existing_variants_fn = lambda item: self.variants_map.get(item, [])
        get_compatibility_mappings_fn = lambda: self.compatibility_map

        return (
            get_bom_items_fn,
            get_template_bom_fn,
            get_item_fn,
            get_variant_attributes_fn,
            get_existing_variants_fn,
            get_compatibility_mappings_fn
        )

    @patch('frappe.db.get_value')
    @patch('template_bom_exploder.generator.dry_run.resolve_bom_tree')
    def test_run_dry_run_success(self, mock_resolve, mock_get_value):
        """Test that all variants resolve successfully and summary is correct."""
        mock_get_value.return_value = self.root_item_code

        # Mock resolver to return 'ok' for both variants
        mock_resolve.return_value = {
            'status': 'ok',
            'resolved_items': [{'resolved_item_code': 'SOME-RESOLVED-CODE'}]
        }

        funcs = self._make_mocks()

        result = run_dry_run(self.template_bom_name, *funcs)

        self.assertEqual(result['template_bom'], self.template_bom_name)
        self.assertEqual(result['summary']['total'], 2)
        self.assertEqual(result['summary']['ok'], 2)
        self.assertEqual(result['summary']['failed'], 0)
        self.assertEqual(len(result['variants']), 2)
        self.assertEqual(result['variants'][0]['status'], 'ok')

    @patch('frappe.db.get_value')
    @patch('template_bom_exploder.generator.dry_run.resolve_bom_tree')
    def test_run_dry_run_with_failures(self, mock_resolve, mock_get_value):
        """Test that the summary correctly identifies failed variants."""
        mock_get_value.return_value = self.root_item_code

        # Side effect: first call returns ok, second returns error
        mock_resolve.side_effect = [
            {'status': 'ok', 'resolved_items': []},
            {'status': 'failed', 'errors': [{'msg': 'Unresolvable item'}]}
        ]

        funcs = self._make_mocks()

        result = run_dry_run(self.template_bom_name, *funcs)

        self.assertEqual(result['summary']['total'], 2)
        self.assertEqual(result['summary']['ok'], 1)
        self.assertEqual(result['summary']['failed'], 1)
        self.assertEqual(result['variants'][1]['status'], 'failed')
        self.assertEqual(result['variants'][1]['error'], {'msg': 'Unresolvable item'})

if __name__ == '__main__':
    unittest.main()
