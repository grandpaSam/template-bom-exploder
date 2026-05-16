# generator/dry_run.py

import frappe
from template_bom_exploder.resolver.resolver import resolve_bom_tree

def run_dry_run(
	template_bom_name,
	get_bom_items_fn,
	get_template_bom_fn,
	get_item_fn,
	get_variant_attributes_fn,
	get_existing_variants_fn,
	get_compatibility_mappings_fn,
):
	"""
	Dry-run phase: resolves all existing variants of the root template item
	against the template BOM tree and returns a structured report for UI confirmation.

	Args:
		template_bom_name:          name of the root template BOM to explode
		get_bom_items_fn:           callable(bom_name) -> list of BOM item dicts
		get_template_bom_fn:        callable(item_code) -> bom_name or None
		get_item_fn:                callable(item_code) -> dict {item_code, variant_of, has_variants}
		get_variant_attributes_fn:  callable(template_item_code) -> list of attribute names
		get_existing_variants_fn:   callable(template_item_code) -> list of variant dicts
		get_compatibility_mappings_fn: callable() -> compatibility map dict

	Returns:
		{
			'template_bom': str,
			'summary': {'total': int, 'ok': int, 'failed': int},
			'variants': [
				{
					'variant_item': str,
					'attributes': dict,
					'status': 'ok' | 'failed',
					'resolved_tree': [...],  # present on ok
					'error': {...} | None    # present on failed
				}
			]
		}
	"""

	# --- 1. Fetch the root template item from the BOM ---
	root_bom_items = get_bom_items_fn(template_bom_name)
	root_template_item = _get_root_template_item(template_bom_name)
	root_item = get_item_fn(root_template_item)
	root_item_name = root_item.get('item_name') or root_template_item

	# --- 2. Pull shared data once — compatibility map is the same for every variant ---
	compatibility_map = get_compatibility_mappings_fn()

	# --- 3. Hydrate the BOM item list with children (recursive) ---
	bom_tree = _hydrate_bom_items(root_bom_items, get_bom_items_fn, get_template_bom_fn, get_item_fn)

	# --- 4. Fetch all existing variants of the root template item ---
	existing_root_variants = get_existing_variants_fn(root_template_item)

	# --- 5. Run the resolver for each variant ---
	variant_results = []

	for variant in existing_root_variants:
		target_attributes = variant['attributes']
		variant_item_code = variant['item_code']
		variant_item      = get_item_fn(variant_item_code)
		variant_item_name = variant_item.get('item_name') or variant_item_code

		result = resolve_bom_tree(
			bom_items=bom_tree,
			target_attributes=target_attributes,
			get_item_fn=get_item_fn,
			get_variant_attributes_fn=get_variant_attributes_fn,
			get_existing_variants_fn=get_existing_variants_fn,
			get_template_bom_fn=get_template_bom_fn,
			compatibility_map=compatibility_map,
		)

		if result['status'] == 'ok':
			variant_results.append({
				'variant_item': variant_item_code,
				'variant_item_name': variant_item_name,
				'attributes': target_attributes,
				'status': 'ok',
				'resolved_tree': result['resolved_items'],
				'error': None,
			})
		else:
			# fail-fast: resolver returns on first error, errors[0] is it
			variant_results.append({
				'variant_item': variant_item_code,
				'variant_item_name': variant_item_name,
				'attributes': target_attributes,
				'status': 'failed',
				'resolved_tree': [],
				'error': result['errors'][0],
			})

	# --- 6. Build summary ---
	total = len(variant_results)
	ok_count = sum(1 for v in variant_results if v['status'] == 'ok')
	return {
		'template_bom': template_bom_name,
		'root_item_code': root_template_item,
		'root_item_name': root_item_name,
		'summary': {
			'total': total,
			'ok': ok_count,
			'failed': total - ok_count,
		},
		'variants': variant_results,
	}


def _get_root_template_item(template_bom_name):
	"""
	Extracts the root template item code from a BOM name.

	BOM names in ERPNext encode the item code — we read it from the BOM doc
	via a minimal frappe.db call rather than parsing the string.
	"""
	return frappe.db.get_value('BOM', template_bom_name, 'item')


def _hydrate_bom_items(bom_items, get_bom_items_fn, get_template_bom_fn, get_item_fn):
	"""
	Recursively attaches 'children' to each BOM item that is a template or
	sub-assembly with its own BOM.

	This mirrors what resolve_bom_tree expects: bom_item.get('children', [])
	is how it recurses into sub-assemblies.

	Args:
		bom_items: flat list of BOM item dicts from get_bom_items_fn()

	Returns:
		same list with 'children' key populated on sub-assembly items
	"""
	hydrated = []
	for bom_item in bom_items:
		item_code = bom_item['item_code']
		if bom_item.get('do_not_explode'):
			hydrated.append({**bom_item, 'children': []})
			continue
		item = get_item_fn(item_code)

		template_item = None
		if item.get('has_variants'):
			template_item = item_code
		elif item.get('variant_of'):
			template_item = item['variant_of']
		children = []

		if template_item:
			# Look for a BOM on the item itself (the standard case)
			sub_bom = get_template_bom_fn(template_item)
		else:
			sub_bom = get_template_bom_fn(item_code)
		if sub_bom:
			sub_items = get_bom_items_fn(sub_bom)
			children = _hydrate_bom_items(sub_items, get_bom_items_fn, get_template_bom_fn, get_item_fn)

		hydrated.append({**bom_item, 'children': children})

	return hydrated

