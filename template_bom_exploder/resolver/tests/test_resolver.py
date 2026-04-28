import unittest
from template_bom_exploder.resolver.resolver import resolve_item, resolve_bom_tree


# ---------------------------------------------------------------------------
# Shared test fixtures based on real item structure
# ---------------------------------------------------------------------------

# Compatibility map matching the real BOM Attribute Compatibility records:
# Caliber-ASR-Lower "9mm/.40Cal/.357Sig" maps to Caliber-ASR "9mm", "40Cal", "357Sig"
# Caliber-ASR-Lower ".45Cal/10mm/.460Rowland" maps to Caliber-ASR "45Cal", "10mm", "460Rowland"
COMPATIBILITY_MAP = {
	('Caliber-ASR', '9mm'): [
		{'source_attribute': 'Caliber-ASR-Lower', 'source_value': '9mm/.40Cal/.357Sig'}
	],
	('Caliber-ASR', '40Cal'): [
		{'source_attribute': 'Caliber-ASR-Lower', 'source_value': '9mm/.40Cal/.357Sig'}
	],
	('Caliber-ASR', '357Sig'): [
		{'source_attribute': 'Caliber-ASR-Lower', 'source_value': '9mm/.40Cal/.357Sig'}
	],
	('Caliber-ASR', '45Cal'): [
		{'source_attribute': 'Caliber-ASR-Lower', 'source_value': '.45Cal/10mm/.460Rowland'}
	],
	('Caliber-ASR', '10mm'): [
		{'source_attribute': 'Caliber-ASR-Lower', 'source_value': '.45Cal/10mm/.460Rowland'}
	],
	('Caliber-ASR', '460Rowland'): [
		{'source_attribute': 'Caliber-ASR-Lower', 'source_value': '.45Cal/10mm/.460Rowland'}
	],
}

# Barrel assembly variants (has both Caliber-ASR and Color-ASR)
BARREL_ASSEMBLY_VARIANTS = [
	{'item_code': 'ASRX-GP03-0009-BK-XX00', 'attributes': {'Caliber-ASR': '9mm', 'Color-ASR': 'Black'}},
	{'item_code': 'ASRX-GP03-0010-BKOD-XX00', 'attributes': {'Caliber-ASR': '10mm', 'Color-ASR': 'OD'}},
]

# Lower assembly variants (has Caliber-ASR-Lower and Color-ASR)
LOWER_ASSEMBLY_VARIANTS = [
	{'item_code': 'ASRX-GP04-0940-BK-XX00', 'attributes': {'Caliber-ASR-Lower': '9mm/.40Cal/.357Sig', 'Color-ASR': 'Black'}},
	{'item_code': 'ASRX-GP04-XX45-BKOD-XX00', 'attributes': {'Caliber-ASR-Lower': '.45Cal/10mm/.460Rowland', 'Color-ASR': 'OD'}},
]

# Barrel nut variants (has only Color-ASR)
BARREL_NUT_VARIANTS = [
	{'item_code': 'ASR-GP03-XXXX-BK-XX01', 'attributes': {'Color-ASR': 'Black'}},
	{'item_code': 'ASR-GP03-XXXX-OD-XX01', 'attributes': {'Color-ASR': 'OD'}},
]

# Rifle barrel variants (has only Caliber-ASR)
RIFLE_BARREL_VARIANTS = [
	{'item_code': 'ASRX-GP03-0009-BKXX-XXXX', 'attributes': {'Caliber-ASR': '9mm'}},
	{'item_code': 'ASRX-GP03-0010-BKXX-XXXX', 'attributes': {'Caliber-ASR': '10mm'}},
]

TRIGGER_HOUSING_VARIANTS = [
	{'item_code': 'ASRX-GP04-0940-BK-XX38', 'attributes': {'Caliber-ASR-Lower': '9mm/.40Cal/.357Sig', 'Color-ASR': 'Black'}},
	{'item_code': 'ASRX-GP04-XX45-BKOD-XX38', 'attributes': {'Caliber-ASR-Lower': '.45Cal/10mm/.460Rowland', 'Color-ASR': 'OD'}},
]


# ---------------------------------------------------------------------------
# resolve_item tests
# ---------------------------------------------------------------------------

class TestResolveItemExactMatch(unittest.TestCase):

	def test_resolves_both_attributes_exact_match(self):
		"""Barrel assembly: both Caliber-ASR and Color-ASR match directly"""
		result = resolve_item(
			'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00',
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			['Caliber-ASR', 'Color-ASR'],
			COMPATIBILITY_MAP,
			BARREL_ASSEMBLY_VARIANTS
		)
		self.assertEqual(result['status'], 'resolved')
		self.assertEqual(result['item_code'], 'ASRX-GP03-0009-BK-XX00')

	def test_resolves_single_attribute_color_only(self):
		"""Barrel nut: only has Color-ASR, should ignore Caliber-ASR from parent context"""
		result = resolve_item(
			'ASR-GP03-XXXX-{Color-ASR}-XX01',
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			['Color-ASR'],
			COMPATIBILITY_MAP,
			BARREL_NUT_VARIANTS
		)
		self.assertEqual(result['status'], 'resolved')
		self.assertEqual(result['item_code'], 'ASR-GP03-XXXX-BK-XX01')

	def test_resolves_single_attribute_caliber_only(self):
		"""Rifle barrel: only has Caliber-ASR, should ignore Color-ASR from parent context"""
		result = resolve_item(
			'ASRX-GP03-{Caliber-ASR}-BKXX-XXXX',
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			['Caliber-ASR'],
			COMPATIBILITY_MAP,
			RIFLE_BARREL_VARIANTS
		)
		self.assertEqual(result['status'], 'resolved')
		self.assertEqual(result['item_code'], 'ASRX-GP03-0009-BKXX-XXXX')


class TestResolveItemCompatibilityMap(unittest.TestCase):

	def test_resolves_lower_assembly_via_compatibility_map_9mm(self):
		"""Lower assembly: Caliber-ASR-Lower resolved via compatibility map for 9mm parent"""
		result = resolve_item(
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00',
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			['Caliber-ASR-Lower', 'Color-ASR'],
			COMPATIBILITY_MAP,
			LOWER_ASSEMBLY_VARIANTS
		)
		self.assertEqual(result['status'], 'resolved')
		self.assertEqual(result['item_code'], 'ASRX-GP04-0940-BK-XX00')

	def test_resolves_lower_assembly_via_compatibility_map_10mm(self):
		"""Lower assembly: Caliber-ASR-Lower resolved via compatibility map for 10mm parent"""
		result = resolve_item(
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00',
			{'Caliber-ASR': '10mm', 'Color-ASR': 'OD'},
			['Caliber-ASR-Lower', 'Color-ASR'],
			COMPATIBILITY_MAP,
			LOWER_ASSEMBLY_VARIANTS
		)
		self.assertEqual(result['status'], 'resolved')
		self.assertEqual(result['item_code'], 'ASRX-GP04-XX45-BKOD-XX00')

	def test_resolves_lower_assembly_40cal(self):
		"""Lower assembly: 40Cal should also map to 9mm/.40Cal/.357Sig lower"""
		result = resolve_item(
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00',
			{'Caliber-ASR': '40Cal', 'Color-ASR': 'Black'},
			['Caliber-ASR-Lower', 'Color-ASR'],
			COMPATIBILITY_MAP,
			LOWER_ASSEMBLY_VARIANTS
		)
		self.assertEqual(result['status'], 'resolved')
		self.assertEqual(result['item_code'], 'ASRX-GP04-0940-BK-XX00')


class TestResolveItemUnresolvable(unittest.TestCase):

	def test_unresolvable_no_mapping_exists(self):
		"""Attribute on item has no direct match and no compatibility mapping"""
		result = resolve_item(
			'SOME-TEMPLATE-ITEM',
			{'Caliber-ASR': '9mm'},
			['Some-Unknown-Attribute'],
			COMPATIBILITY_MAP,
			[]
		)
		self.assertEqual(result['status'], 'unresolvable')

	def test_unresolvable_mapped_attribute_not_on_item(self):
		"""Compatibility map returns a source_attribute the item doesn't actually have"""
		result = resolve_item(
			'SOME-TEMPLATE-ITEM',
			{'Caliber-ASR': '9mm'},
			['Caliber-ASR-Lower'],
			COMPATIBILITY_MAP,
			# Variants that don't have Caliber-ASR-Lower at all
			[{'item_code': 'SOME-VARIANT', 'attributes': {'Some-Other-Attr': 'foo'}}]
		)
		self.assertEqual(result['status'], 'unresolvable')

	def test_unresolvable_no_variant_exists_for_resolved_attributes(self):
		"""Attributes resolve correctly but no variant item exists for that combination"""
		result = resolve_item(
			'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00',
			{'Caliber-ASR': '50BMG', 'Color-ASR': 'Black'},
			['Caliber-ASR', 'Color-ASR'],
			COMPATIBILITY_MAP,
			BARREL_ASSEMBLY_VARIANTS
		)
		self.assertEqual(result['status'], 'unresolvable')


class TestResolveItemAmbiguous(unittest.TestCase):

	def test_ambiguous_multiple_compatible_source_values(self):
		"""Two different source values both map to the same target — ambiguous"""
		ambiguous_map = {
			('Caliber-ASR', '9mm'): [
				{'source_attribute': 'Caliber-ASR-Lower', 'source_value': '9mm/.40Cal/.357Sig'},
				{'source_attribute': 'Caliber-ASR-Lower', 'source_value': '9mm-only'},
			]
		}
		result = resolve_item(
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00',
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			['Caliber-ASR-Lower', 'Color-ASR'],
			ambiguous_map,
			LOWER_ASSEMBLY_VARIANTS
		)
		self.assertEqual(result['status'], 'ambiguous')

	def test_ambiguous_multiple_variants_match_same_attributes(self):
		"""Two variant items have identical attribute sets — should be ambiguous"""
		duplicate_variants = [
			{'item_code': 'ASRX-GP03-0009-BK-XX00', 'attributes': {'Caliber-ASR': '9mm', 'Color-ASR': 'Black'}},
			{'item_code': 'ASRX-GP03-0009-BK-XX00-DUP', 'attributes': {'Caliber-ASR': '9mm', 'Color-ASR': 'Black'}},
		]
		result = resolve_item(
			'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00',
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			['Caliber-ASR', 'Color-ASR'],
			COMPATIBILITY_MAP,
			duplicate_variants
		)
		self.assertEqual(result['status'], 'ambiguous')


# ---------------------------------------------------------------------------
# resolve_bom_tree tests
# ---------------------------------------------------------------------------

def make_item_fn(item_map):
	"""Factory for a mock get_item_fn from a dict"""
	def get_item_fn(item_code):
		return item_map.get(item_code, {'item_code': item_code, 'variant_of': None, 'has_variants': False})
	return get_item_fn


def make_variant_attributes_fn(attr_map):
	def get_variant_attributes_fn(template_item):
		return attr_map.get(template_item, [])
	return get_variant_attributes_fn


def make_existing_variants_fn(variants_map):
	def get_existing_variants_fn(template_item):
		return variants_map.get(template_item, [])
	return get_existing_variants_fn


def make_template_bom_fn(bom_map):
	def get_template_bom_fn(item_code):
		return bom_map.get(item_code)
	return get_template_bom_fn


class TestResolveBomTree(unittest.TestCase):

	def setUp(self):
		self.item_map = {
			'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00': {'item_code': 'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00', 'variant_of': None, 'has_variants': True},
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00': {'item_code': 'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00', 'variant_of': None, 'has_variants': True},
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX38': {'item_code': 'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX38', 'variant_of': None, 'has_variants': True},
			'ASR-GP03-XXXX-{Color-ASR}-XX01': {'item_code': 'ASR-GP03-XXXX-{Color-ASR}-XX01', 'variant_of': None, 'has_variants': True},
			'ASRX-GP03-XXXX-XXXX-0004': {'item_code': 'ASRX-GP03-XXXX-XXXX-0004', 'variant_of': None, 'has_variants': False},
			'ASRX-GP04-XXXX-XXXX-TRIG': {'item_code': 'ASRX-GP04-XXXX-XXXX-TRIG', 'variant_of': None, 'has_variants': False},
			'ASRX-GP04-XXXX-XXXX-TP01': {'item_code': 'ASRX-GP04-XXXX-XXXX-TP01', 'variant_of': None, 'has_variants': False},
			'ASRX-GP04-XXXX-XXXX-TP02': {'item_code': 'ASRX-GP04-XXXX-XXXX-TP02', 'variant_of': None, 'has_variants': False},
		}
		self.attr_map = {
			'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00': ['Caliber-ASR', 'Color-ASR'],
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00': ['Caliber-ASR-Lower', 'Color-ASR'],
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX38': ['Caliber-ASR-Lower', 'Color-ASR'],
			'ASR-GP03-XXXX-{Color-ASR}-XX01': ['Color-ASR'],
		}
		self.variants_map = {
			'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00': BARREL_ASSEMBLY_VARIANTS,
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00': LOWER_ASSEMBLY_VARIANTS,
			'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX38': TRIGGER_HOUSING_VARIANTS,
			'ASR-GP03-XXXX-{Color-ASR}-XX01': BARREL_NUT_VARIANTS,
		}
		self.bom_map = {
			# Lower assembly has a BOM containing the trigger housing and non-template items
			'ASRX-GP04-0940-BK-XX00': 'BOM-ASRX-GP04-0940-BK-XX00',
			'ASRX-GP04-XX45-BKOD-XX00': 'BOM-ASRX-GP04-XX45-BKOD-XX00',
		}
		self.lower_bom_items = [
			{'item_code': 'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX38', 'qty': 1, 'uom': 'Nos'},
			{'item_code': 'ASRX-GP04-XXXX-XXXX-TRIG', 'qty': 1, 'uom': 'Nos'},
			{'item_code': 'ASRX-GP04-XXXX-XXXX-TP01', 'qty': 2, 'uom': 'Nos'},
		]
	def test_non_template_item_passes_through(self):
		"""Snap ring has no variants — should pass through untouched"""
		bom_items = [{'item_code': 'ASRX-GP03-XXXX-XXXX-0004', 'qty': 1, 'uom': 'Nos'}]
		result = resolve_bom_tree(
			bom_items,
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			make_item_fn(self.item_map),
			make_variant_attributes_fn(self.attr_map),
			make_existing_variants_fn(self.variants_map),
			make_template_bom_fn(self.bom_map),
			COMPATIBILITY_MAP
		)
		self.assertEqual(result['status'], 'ok')
		self.assertEqual(result['resolved_items'][0]['resolved_item_code'], 'ASRX-GP03-XXXX-XXXX-0004')

	def test_resolves_barrel_assembly(self):
		"""Barrel assembly resolves to correct variant for 9mm/Black"""
		bom_items = [{'item_code': 'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00', 'qty': 1, 'uom': 'Nos'}]
		result = resolve_bom_tree(
			bom_items,
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			make_item_fn(self.item_map),
			make_variant_attributes_fn(self.attr_map),
			make_existing_variants_fn(self.variants_map),
			make_template_bom_fn(self.bom_map),
			COMPATIBILITY_MAP
		)
		__import__('pprint').pprint(result)
		self.assertEqual(result['status'], 'ok')
		self.assertEqual(result['resolved_items'][0]['resolved_item_code'], 'ASRX-GP03-0009-BK-XX00')

	def test_resolves_lower_assembly_via_compatibility_map(self):
		"""Lower assembly resolves via compatibility map for 9mm/Black"""
		bom_items = [{'item_code': 'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00', 'qty': 1, 'uom': 'Nos'}]
		result = resolve_bom_tree(
			bom_items,
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			make_item_fn(self.item_map),
			make_variant_attributes_fn(self.attr_map),
			make_existing_variants_fn(self.variants_map),
			make_template_bom_fn(self.bom_map),
			COMPATIBILITY_MAP
		)
		self.assertEqual(result['status'], 'ok')
		self.assertEqual(result['resolved_items'][0]['resolved_item_code'], 'ASRX-GP04-0940-BK-XX00')

	def test_full_bom_resolves_all_items(self):
		"""Full root BOM with mixed template and non-template items all resolve correctly"""
		bom_items = [
			{'item_code': 'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00', 'qty': 1, 'uom': 'Nos'},
			{'item_code': 'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00', 'qty': 1, 'uom': 'Nos'},
			{'item_code': 'ASRX-GP03-XXXX-XXXX-0004', 'qty': 1, 'uom': 'Nos'},
		]
		result = resolve_bom_tree(
			bom_items,
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			make_item_fn(self.item_map),
			make_variant_attributes_fn(self.attr_map),
			make_existing_variants_fn(self.variants_map),
			make_template_bom_fn(self.bom_map),
			COMPATIBILITY_MAP
		)
		self.assertEqual(result['status'], 'ok')
		codes = [i['resolved_item_code'] for i in result['resolved_items']]
		self.assertIn('ASRX-GP03-0009-BK-XX00', codes)
		self.assertIn('ASRX-GP04-0940-BK-XX00', codes)
		self.assertIn('ASRX-GP03-XXXX-XXXX-0004', codes)

	def test_unresolvable_item_fails_entire_tree(self):
		"""If any item is unresolvable the whole tree should fail"""
		bom_items = [
			{'item_code': 'ASRX-GP03-{Caliber-ASR}-{Color-ASR}-XX00', 'qty': 1, 'uom': 'Nos'},
			{'item_code': 'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00', 'qty': 1, 'uom': 'Nos'},
		]
		# Use a context with a caliber that has no mapping for the lower
		result = resolve_bom_tree(
			bom_items,
			{'Caliber-ASR': '50BMG', 'Color-ASR': 'Black'},
			make_item_fn(self.item_map),
			make_variant_attributes_fn(self.attr_map),
			make_existing_variants_fn(self.variants_map),
			make_template_bom_fn(self.bom_map),
			COMPATIBILITY_MAP
		)
		self.assertEqual(result['status'], 'failed')
		self.assertTrue(len(result['errors']) > 0)

	def test_circular_reference_detected(self):
		"""Circular BOM reference should be caught and reported"""
		circular_item_map = {
			'ITEM-A': {'item_code': 'ITEM-A', 'variant_of': None, 'has_variants': True},
		}
		bom_items = [{'item_code': 'ITEM-A', 'qty': 1, 'uom': 'Nos', 'children': []}]
		visited = {'ITEM-A'}  # Pre-populate visited to simulate circular ref
		result = resolve_bom_tree(
			bom_items,
			{'Caliber-ASR': '9mm'},
			make_item_fn(circular_item_map),
			make_variant_attributes_fn({}),
			make_existing_variants_fn({}),
			make_template_bom_fn({}),
			COMPATIBILITY_MAP,
			visited=visited
		)
		self.assertEqual(result['status'], 'failed')
	def test_fully_resolved_tree_with_sub_assembly(self):
		"""Full tree: lower assembly resolves and recurses into trigger housing with leaf items"""
		bom_items = [
			{
				'item_code': 'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00',
				'qty': 1,
				'uom': 'Nos',
				'children': self.lower_bom_items
			},
		]
		result = resolve_bom_tree(
			bom_items,
			{'Caliber-ASR': '9mm', 'Color-ASR': 'Black'},
			make_item_fn(self.item_map),
			make_variant_attributes_fn(self.attr_map),
			make_existing_variants_fn(self.variants_map),
			make_template_bom_fn(self.bom_map),
			COMPATIBILITY_MAP
		)
		self.assertEqual(result['status'], 'ok')

		# Top level — lower assembly resolved
		lower = result['resolved_items'][0]
		self.assertEqual(lower['resolved_item_code'], 'ASRX-GP04-0940-BK-XX00')

		# Children — trigger housing resolved, leaf items passed through
		children = lower['children']
		child_codes = [c['resolved_item_code'] for c in children]
		self.assertIn('ASRX-GP04-0940-BK-XX38', child_codes)
		self.assertIn('ASRX-GP04-XXXX-XXXX-TRIG', child_codes)
		self.assertIn('ASRX-GP04-XXXX-XXXX-TP01', child_codes)


if __name__ == '__main__':
	unittest.main()
