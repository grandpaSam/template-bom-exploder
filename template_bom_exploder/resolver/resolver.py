def resolve_item(template_item_code, target_attributes, item_variant_attributes, compatibility_map, existing_variants):
	"""
	Resolves a template item to a concrete variant given a set of target attributes.

	Args:
		template_item_code: the template item we are trying to resolve (e.g. 'ASRX-GP04-{Caliber-ASR-Lower}-{Color-ASR}-XX00')
		target_attributes: dict of attribute->value from the parent context (e.g. {'Caliber-ASR': '9mm', 'Color-ASR': 'Black'})
		item_variant_attributes: list of attributes this template item has (e.g. ['Caliber-ASR-Lower', 'Color-ASR'])
		compatibility_map: the full compatibility map from data.get_compatibility_mappings()
		existing_variants: list of variant dicts from data.get_existing_variants()

	Returns:
		{'status': 'resolved', 'item_code': '...'}
		{'status': 'unresolvable', 'reason': '...'}
		{'status': 'ambiguous', 'candidates': [...]}
	"""
	resolved_attributes = {}

	for attribute in item_variant_attributes:

		# Case 1: direct match — parent has this attribute
		if attribute in target_attributes:
			resolved_attributes[attribute] = target_attributes[attribute]
			continue

		# Case 2: compatibility table lookup
		matched_sources = []
		for (target_attr, target_val), sources in compatibility_map.items():
			if target_attr not in target_attributes:
				continue
			if target_attributes[target_attr] != target_val:
				continue
			# This mapping's target matches our parent context.
			# Check if any source in this mapping matches our current attribute
			for source in sources:
				if source['source_attribute'] == attribute:
					matched_sources.append(source['source_value'])

		if len(matched_sources) == 0:
			return {
				'status': 'unresolvable',
				'reason': (
					f'Attribute "{attribute}" on item "{template_item_code}" '
					f'has no direct match or compatibility mapping for the current context: {target_attributes}'
				)
			}

		if len(matched_sources) > 1:
			return {
				'status': 'ambiguous',
				'reason': (
					f'Attribute "{attribute}" on item "{template_item_code}" '
					f'matched multiple compatibility sources: {matched_sources}'
				),
				'candidates': matched_sources
			}

		resolved_attributes[attribute] = matched_sources[0]

	# Now find the variant that matches resolved_attributes exactly
	matching_variants = []
	for variant in existing_variants:
		if variant['attributes'] == resolved_attributes:
			matching_variants.append(variant['item_code'])

	if len(matching_variants) == 0:
		return {
			'status': 'unresolvable',
			'reason': (
				f'No variant of "{template_item_code}" found with attributes: {resolved_attributes}'
			)
		}

	if len(matching_variants) > 1:
		return {
			'status': 'ambiguous',
			'reason': (
				f'Multiple variants of "{template_item_code}" matched attributes: {resolved_attributes}'
			),
			'candidates': matching_variants
		}

	return {
		'status': 'resolved',
		'item_code': matching_variants[0]
	}


def resolve_bom_tree(bom_items, target_attributes, get_item_fn, get_variant_attributes_fn, get_existing_variants_fn, get_template_bom_fn, compatibility_map, visited=None):
	"""
	Recursively resolves a list of BOM items to concrete variant item codes.

	Walks the BOM tree depth-first. For each item:
	- Non-template items pass through as-is
	- Template items are resolved via resolve_item() using target_attributes as context
	- If a resolved item has its own BOM, recurses into it with the same target_attributes

	The same target_attributes flow unchanged through the entire recursion — they always
	represent the root variant being built (e.g. {'Caliber-ASR': '9mm', 'Color-ASR': 'Black'}).
	Sub-assemblies use only the attributes relevant to them and ignore the rest.

	Args:
		bom_items: list of BOM item dicts from the parent BOM (each has at minimum 'item_code')
		target_attributes: dict of attribute->value representing the root variant being built
		                   (e.g. {'Caliber-ASR': '9mm', 'Color-ASR': 'Black'})
		get_item_fn: callable(item_code) -> dict with keys 'item_code', 'variant_of', 'has_variants'
		get_variant_attributes_fn: callable(template_item_code) -> list of attribute names
		get_existing_variants_fn: callable(template_item_code) -> list of variant dicts
		                          each with keys 'item_code' and 'attributes' (dict)
		get_template_bom_fn: callable(item_code) -> bom_name or None
		compatibility_map: the full compatibility map from data.get_compatibility_mappings()
		visited: set of already-visited item codes and BOM names used for circular reference detection

	Returns:
		{'status': 'ok', 'resolved_items': [...]}
		{'status': 'failed', 'errors': [...]}
	"""
	if visited is None:
		visited = set()

	resolved_items = []
	errors = []

	for bom_item in bom_items:
		item_code = bom_item['item_code']
		item = get_item_fn(item_code)

		# Case 3: not a template item, use as-is
		if not item.get('variant_of') and not item.get('has_variants'):
			resolved_items.append({**bom_item, 'resolved_item_code': item_code, 'resolved_item_name': item.get('item_name') or item_code})
			continue

		# Circular reference guard
		if item_code in visited:
			errors.append({
				'item_code': item_code,
				'reason': f'Circular BOM reference detected for item "{item_code}"'
			})
			continue

		visited.add(item_code)

		# Get the template item code
		template_item = item_code if item.get('has_variants') else item.get('variant_of')

		variant_attributes = get_variant_attributes_fn(template_item)
		existing_variants = get_existing_variants_fn(template_item)

		result = resolve_item(
			template_item,
			target_attributes,
			variant_attributes,
			compatibility_map,
			existing_variants
		)

		if result['status'] != 'resolved':
			errors.append({
				'item_code': item_code,
				**result
			})
			continue

		resolved_item_code = result['item_code']
		resolved_item = get_item_fn(resolved_item_code)
		resolved_item_name = resolved_item.get('item_name') or resolved_item_code

		# Respect "Do Not Explode" — treat as a leaf even if a sub-BOM exists
		if bom_item.get('custom_do_not_explode_for_template'):
			resolved_items.append({
				**bom_item,
				'resolved_item_code': resolved_item_code,
				'resolved_item_name': resolved_item_name,
			})
			continue
		# Recurse into sub-assembly if it has its own BOM
		sub_bom = get_template_bom_fn(resolved_item_code)
		if not sub_bom:
			# Try the template item's BOM as fallback
			sub_bom = get_template_bom_fn(template_item)

		if sub_bom:
			if sub_bom in visited:
				errors.append({
					'item_code': resolved_item_code,
					'reason': f'Circular BOM reference detected for BOM "{sub_bom}"'
				})
				continue

			visited.add(sub_bom)

			sub_bom_items_result = resolve_bom_tree(
				bom_item.get('children', []),
				target_attributes,
				get_item_fn,
				get_variant_attributes_fn,
				get_existing_variants_fn,
				get_template_bom_fn,
				compatibility_map,
				visited
			)

			if sub_bom_items_result['status'] == 'failed':
				errors.extend(sub_bom_items_result['errors'])
				continue

			resolved_items.append({
				**bom_item,
				'resolved_item_code': resolved_item_code,
				'resolved_item_name': resolved_item_name,
				'children': sub_bom_items_result['resolved_items']
			})
		else:
			resolved_items.append({
				**bom_item,
				'resolved_item_code': resolved_item_code,
				'resolved_item_name': resolved_item_name,
			})

		visited.discard(item_code)

	if errors:
		return {'status': 'failed', 'errors': errors}

	return {'status': 'ok', 'resolved_items': resolved_items}
